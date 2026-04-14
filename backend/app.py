"""
RAG Visual Chatbot Backend - v8 CLEAN
======================================
Clean, optimized RAG pipeline:
1. INDEX: Vision → Page context → Web search → All into FAISS
2. RETRIEVE: Query → FAISS similarity search → Top-k chunks
3. GENERATE: LLM with retrieved context → Grounded answer

No product search. Focused on accurate visual Q&A.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from PIL import Image
from io import BytesIO
import faiss
import numpy as np
import logging
import base64
import hashlib
import re
from collections import Counter
from sentence_transformers import SentenceTransformer
import ollama
import bs4

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

# ── Models ────────────────────────────────────────────────────────────────────
logger.info("Loading sentence-transformer...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

EMBED_DIM     = 384
VISION_MODELS = ["moondream", "llava:7b", "llava"]
LLM_MODELS    = ["llama3.2", "llama3", "mistral"]

# ── In-memory store ───────────────────────────────────────────────────────────
index          = faiss.IndexFlatL2(EMBED_DIM)
document_store = []   # [{text, source, type, image_url}]
image_cache    = {}   # url_hash → {caption, b64, page_ctx, search_topic}


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_available_models():
    try:
        result = ollama.list()
        if isinstance(result, dict):
            return [m.get("name", m.get("model", "")) for m in result.get("models", [])]
        return [m.model for m in result.models]
    except:
        return ["llama3.2"]


def get_vision_model():
    avail = get_available_models()
    for v in VISION_MODELS:
        for m in avail:
            if v.split(":")[0] in m:
                return m
    return None


def get_llm():
    avail = get_available_models()
    for v in LLM_MODELS:
        for m in avail:
            if v in m:
                return m
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def image_to_base64(url: str, max_size: int = 400) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        img.thumbnail((max_size, max_size))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception as e:
        logger.error(f"Image fetch failed: {e}")
        return None


def run_vision_model(b64: str) -> str:
    """Run vision model once. Returns detailed description."""
    model = get_vision_model()
    if not model or not b64:
        return ""
    try:
        resp = ollama.chat(
            model=model,
            messages=[{
                "role": "user",
                "content": (
                    "Describe this image in full detail. Include: "
                    "all visible objects, people (appearance, expression, clothing), "
                    "text visible in the image, colors, materials, setting/environment, "
                    "any brand names, logos, or recognizable elements. "
                    "Be specific and thorough."
                ),
                "images": [b64]
            }],
            options={"num_predict": 350}
        )
        return resp["message"]["content"]
    except Exception as e:
        logger.error(f"Vision model failed: {e}")
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONTEXT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_page_context(page_url: str, image_url: str = "") -> dict:
    """
    Extract structured context from the webpage:
    - Image alt text & figcaption (best for identification)
    - Text surrounding the image
    - Page H1 / product name
    - Repeated proper nouns (page subjects)
    - Full text for chunking
    """
    ctx = {
        "alt_text": "", "figcaption": "", "nearby_text": "",
        "h1": "", "names": [], "full_text": "", "title": ""
    }
    try:
        r    = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        soup = bs4.BeautifulSoup(r.text, "html.parser")

        ctx["title"] = (soup.title.string or "").strip()

        h1 = soup.find("h1")
        if h1:
            ctx["h1"] = h1.get_text(strip=True)[:120]

        if image_url:
            fname   = image_url.split("/")[-1].split("?")[0]
            img_tag = (
                soup.find("img", src=lambda s: s and (image_url in s or fname in s))
                or soup.find("img", attrs={"data-src": lambda s: s and fname in s})
            )
            if img_tag:
                ctx["alt_text"] = img_tag.get("alt", "").strip()

                # Walk up DOM to find figcaption
                parent = img_tag.parent
                for _ in range(4):
                    if parent:
                        fig = parent.find("figcaption")
                        if fig:
                            ctx["figcaption"] = fig.get_text(strip=True)
                            break
                        parent = parent.parent

                # Adjacent text nodes
                nearby = []
                for s in list(img_tag.find_previous_siblings(limit=3))[::-1]:
                    t = s.get_text(strip=True)
                    if t and len(t) > 12:
                        nearby.append(t[:200])
                for s in img_tag.find_next_siblings(limit=3):
                    t = s.get_text(strip=True)
                    if t and len(t) > 12:
                        nearby.append(t[:200])
                ctx["nearby_text"] = " | ".join(nearby)[:600]

        # Full text
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        ctx["full_text"] = soup.get_text(separator=" ", strip=True)[:5000]

        # Repeated capitalized words → likely names/subjects
        words  = ctx["full_text"].split()
        caps   = [w.strip(".,;:!?\"'()[]") for w in words if w and w[0].isupper() and len(w) > 2]
        counts = Counter(caps)
        ctx["names"] = [n for n, c in counts.most_common(12) if c >= 2]

        logger.info(
            f"Page ctx — alt:'{ctx['alt_text'][:40]}' "
            f"h1:'{ctx['h1'][:40]}' names:{ctx['names'][:4]}"
        )
    except Exception as e:
        logger.error(f"Page scrape failed: {e}")
    return ctx


def get_search_topic(page_ctx: dict, caption: str) -> str:
    """Best possible search topic. Avoids generic/useless strings."""
    GENERIC = {"google", "search", "pinterest", "image", "photo", "pin",
               "tbn", "encrypted", "gstatic", "result", "undefined"}

    candidates = [
        page_ctx.get("h1", ""),
        page_ctx.get("alt_text", ""),
        page_ctx.get("figcaption", ""),
        page_ctx.get("nearby_text", "")[:80],
        page_ctx.get("title", ""),
    ]
    for c in candidates:
        c = c.strip()
        if c and len(c) > 5:
            if not any(g in c.lower() for g in GENERIC):
                return c[:80]

    # Fall back to first sentence of caption
    if caption:
        first = caption.split(".")[0].strip()
        return first[:70]
    return ""


# ═══════════════════════════════════════════════════════════════════════════════
# WEB SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

def web_search(query: str, max_results: int = 5) -> list:
    """DuckDuckGo search — free, no API key."""
    if not DDGS or not query.strip():
        return []
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query.strip()[:120], max_results=max_results):
                snippet = r.get("body", "")
                if snippet:
                    results.append({
                        "title":   r.get("title", ""),
                        "snippet": snippet[:300],
                        "url":     r.get("href", "")
                    })
        logger.info(f"Web search '{query[:50]}' → {len(results)} results")
        return results
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# FAISS INDEX
# ═══════════════════════════════════════════════════════════════════════════════

def index_texts(texts: list, source: str, doc_type: str, image_url: str = ""):
    if not texts:
        return
    clean = [t.strip() for t in texts if t and t.strip() and len(t.strip()) > 5]
    if not clean:
        return
    embeddings = embedder.encode(clean, convert_to_numpy=True).astype(np.float32)
    index.add(embeddings)
    for text in clean:
        document_store.append({
            "text":      text,
            "source":    source,
            "type":      doc_type,
            "image_url": image_url
        })
    logger.info(f"  +{len(clean)} [{doc_type}] → total {index.ntotal}")


def retrieve(query: str, top_k: int = 7, image_url: str = "") -> list:
    """
    FAISS retrieval with image-context boosting.
    Chunks from the current image's context get a relevance boost.
    """
    if index.ntotal == 0:
        return []

    q_emb      = embedder.encode([query], convert_to_numpy=True).astype(np.float32)
    k          = min(top_k * 2, index.ntotal)
    distances, idxs = index.search(q_emb, k)

    results = []
    for i, idx in enumerate(idxs[0]):
        if idx == -1:
            continue
        doc   = document_store[idx]
        score = float(distances[0][i])
        # Boost chunks from the current image (lower L2 = better)
        if image_url and doc.get("image_url") == image_url:
            score *= 0.65
        results.append({**doc, "score": score})

    results.sort(key=lambda x: x["score"])
    return results[:top_k]


def chunk_text(text: str, size: int = 200, overlap: int = 30) -> list:
    words = text.split()
    return [
        " ".join(words[i:i + size])
        for i in range(0, len(words), size - overlap)
        if words[i:i + size]
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# QUERY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def classify_query(query: str) -> str:
    q = query.lower()

    if any(p in q for p in [
        "what is in", "what's in", "describe", "what do you see",
        "what can you see", "what is shown", "what does the image",
        "tell me what", "explain the image", "what is depicted"
    ]):
        return "describe"

    if any(p in q for p in [
        "who is", "who are", "what is this", "what is that",
        "identify", "recognize", "name of", "what kind",
        "what type", "what species", "what breed", "what movie",
        "what show", "what cartoon", "what brand", "which"
    ]):
        return "identify"

    if any(p in q for p in [
        "when", "where was", "history of", "how old", "born",
        "nationality", "famous for", "known for", "biography",
        "net worth", "career", "achievement", "award", "founded"
    ]):
        return "factual"

    if any(p in q for p in [
        "how many", "count", "what color", "what colour",
        "what text", "what does it say", "read the", "is there",
        "are there", "can you see", "what number", "zoom"
    ]):
        return "visual_detail"

    return "general"


def build_live_search_query(query: str, search_topic: str) -> str:
    filler = [
        "what is", "what are", "who is", "who are", "tell me about",
        "can you tell", "the image", "this image", "in the image",
        "in the photo", "of the", "about the", "what's"
    ]
    q = query.lower()
    for f in filler:
        q = q.replace(f, " ")
    q = re.sub(r'\s+', ' ', q).strip()[:50]

    return f"{search_topic} {q}".strip()[:100] if search_topic else q


# ═══════════════════════════════════════════════════════════════════════════════
# FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    return jsonify({
        "status":       "ok",
        "indexed_docs": len(document_store),
        "models":       get_available_models(),
        "search":       DDGS is not None
    })


@app.route("/process-image", methods=["POST", "OPTIONS"])
def process_image():
    """
    INDEX PHASE — called once per image.
    Runs vision model, scrapes page, web searches topic.
    Everything indexed into FAISS for RAG retrieval.
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data       = request.json
    image_url  = data.get("image_url", "")
    page_url   = data.get("page_url", "")
    page_title = data.get("page_title", "")

    if not image_url:
        return jsonify({"error": "image_url required"}), 400

    cache_key = hashlib.md5(image_url.encode()).hexdigest()
    if cache_key in image_cache:
        cached = image_cache[cache_key]
        return jsonify({"caption": cached["caption"], "status": "cached"})

    logger.info(f"=== INDEX START: {image_url[:70]} ===")

    # ── 1. Vision model (once) ────────────────────────────────────────────────
    b64     = image_to_base64(image_url)
    caption = run_vision_model(b64) if b64 else ""
    logger.info(f"Vision caption: {caption[:80]}..." if caption else "Vision: none")

    if caption:
        index_texts([caption], source=image_url,
                    doc_type="vision_description", image_url=image_url)

    # ── 2. Page context ───────────────────────────────────────────────────────
    page_ctx = {}
    if page_url:
        page_ctx = extract_page_context(page_url, image_url)

    if page_ctx.get("alt_text"):
        index_texts([f"Image alt text: {page_ctx['alt_text']}"],
                    source=page_url, doc_type="alt_text", image_url=image_url)

    if page_ctx.get("figcaption"):
        index_texts([f"Image caption: {page_ctx['figcaption']}"],
                    source=page_url, doc_type="figcaption", image_url=image_url)

    if page_ctx.get("h1"):
        index_texts([f"Page heading: {page_ctx['h1']}"],
                    source=page_url, doc_type="h1", image_url=image_url)

    if page_ctx.get("nearby_text"):
        index_texts([f"Text near image: {page_ctx['nearby_text']}"],
                    source=page_url, doc_type="nearby_text", image_url=image_url)

    if page_ctx.get("names"):
        index_texts([f"Key subjects on page: {', '.join(page_ctx['names'][:8])}"],
                    source=page_url, doc_type="page_names", image_url=image_url)

    if page_title:
        index_texts([f"Page title: {page_title}"],
                    source=page_url, doc_type="page_title", image_url=image_url)

    if page_ctx.get("full_text"):
        index_texts(chunk_text(page_ctx["full_text"]),
                    source=page_url, doc_type="page_content", image_url=image_url)

    # ── 3. Web search on topic → index results ────────────────────────────────
    search_topic = get_search_topic(page_ctx, caption)
    logger.info(f"Search topic: '{search_topic}'")

    if search_topic and len(search_topic) > 5:
        web_results = web_search(search_topic, max_results=6)
        for r in web_results:
            index_texts(
                [f"{r['title']}: {r['snippet']}"],
                source=r["url"], doc_type="web_search", image_url=image_url
            )

    # ── 4. Cache ──────────────────────────────────────────────────────────────
    display_caption = caption or search_topic or "Image indexed."
    if page_ctx.get("alt_text") and caption:
        display_caption = f"{caption[:200]}..."

    image_cache[cache_key] = {
        "caption":      display_caption,
        "b64":          b64,
        "page_ctx":     page_ctx,
        "search_topic": search_topic,
        "image_url":    image_url
    }

    logger.info(f"=== INDEX DONE. Total FAISS chunks: {index.ntotal} ===")
    return jsonify({"caption": display_caption, "status": "processed"})


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    """
    RETRIEVE + GENERATE PHASE.
    Pure RAG: query → FAISS → top-k chunks → LLM → answer.
    Live web search only for factual/identify queries.
    """
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data      = request.json
    query     = data.get("query", "")
    image_url = data.get("image_url", "")

    if not query:
        return jsonify({"error": "query required"}), 400

    # Get cached image data
    cached = {}
    if image_url:
        cached = image_cache.get(hashlib.md5(image_url.encode()).hexdigest(), {})

    search_topic = cached.get("search_topic", "")
    caption      = cached.get("caption", "")

    query_type = classify_query(query)
    logger.info(f"Query type: {query_type} | '{query[:50]}'")

    context_parts = []
    sources_used  = []

    # ── RAG RETRIEVAL (core) ──────────────────────────────────────────────────
    retrieved = retrieve(query, top_k=7, image_url=image_url)

    if retrieved:
        # Group by chunk type for structured prompt
        by_type = {}
        for r in retrieved:
            by_type.setdefault(r["type"], []).append(r)

        # Vision description — primary visual context
        vision = by_type.get("vision_description", [])
        if vision:
            context_parts.append(
                "Visual analysis of the image:\n" +
                "\n".join(f"  {c['text']}" for c in vision)
            )
            sources_used.append("vision model")

        # Identification chunks — alt text, captions, names
        id_types  = ["alt_text", "figcaption", "h1", "nearby_text", "page_names", "page_title"]
        id_chunks = [c for t in id_types for c in by_type.get(t, [])]
        if id_chunks:
            context_parts.append(
                "Identification context from the page:\n" +
                "\n".join(f"  {c['text']}" for c in id_chunks)
            )
            sources_used.append("page context")

        # Pre-indexed web results
        web_chunks = by_type.get("web_search", [])
        if web_chunks:
            context_parts.append(
                "Pre-fetched web knowledge:\n" +
                "\n".join(f"  {c['text'][:220]}" for c in web_chunks)
            )
            sources_used.append("indexed web")

        # Page text chunks
        page_chunks = by_type.get("page_content", [])
        if page_chunks:
            context_parts.append(
                "Page content:\n" +
                "\n".join(f"  {c['text'][:160]}" for c in page_chunks[:3])
            )

    # ── Live web search for identify/factual ──────────────────────────────────
    if query_type in ("identify", "factual"):
        live_q       = build_live_search_query(query, search_topic)
        live_results = web_search(live_q, max_results=5)
        if live_results:
            context_parts.append(
                f"Live web search for '{live_q}':\n" +
                "\n".join(
                    f"  {r['title']}: {r['snippet']}"
                    for r in live_results if r.get("snippet")
                )
            )
            sources_used.append("live web search")
            # Index for future questions in this session
            for r in live_results:
                index_texts(
                    [f"{r['title']}: {r['snippet']}"],
                    source=r["url"], doc_type="web_search", image_url=image_url
                )

    # ── Build LLM prompt ──────────────────────────────────────────────────────
    full_context = "\n\n---\n\n".join(context_parts) if context_parts else "No context available yet."

    task_map = {
        "describe":      "Give a clear, detailed description of the image using the visual analysis.",
        "identify":      "Identify specifically WHO or WHAT this is. Use the identification context and web results. State the name/identity directly and confidently.",
        "factual":       "Answer with precise facts. Use dates, names, numbers from the web results.",
        "visual_detail": "Answer the specific visual detail question using the image analysis.",
        "general":       "Answer the question directly and helpfully using all available context.",
    }
    task = task_map.get(query_type, task_map["general"])

    prompt = f"""You are a visual assistant embedded in a browser extension. The user is looking at an image on a webpage.

RETRIEVED CONTEXT (RAG):
{full_context}

USER QUESTION: {query}

YOUR TASK: {task}

RULES:
- Be direct and specific — no hedging or vagueness
- If alt text or page context names a person/place/thing, USE that name
- Use web results to give factual, current information
- Never say "search the internet" — you already have web results above
- Answer in 2-5 sentences unless the question needs more detail
- Do not fabricate information not present in the context"""

    llm = get_llm()
    if not llm:
        return jsonify({
            "answer":  "No LLM found. Run: ollama pull llama3.2",
            "sources": [],
            "confidence": 0
        })

    try:
        resp = ollama.chat(
            model=llm,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 450}
        )
        answer = resp["message"]["content"]
    except Exception as e:
        logger.error(f"LLM error: {e}")
        answer = f"Error generating response: {e}"

    # Simple confidence: based on how much context we retrieved
    confidence = min(0.95, 0.3 + (len(context_parts) * 0.15) + (len(retrieved) * 0.04))

    return jsonify({
        "answer":     answer,
        "sources":    sources_used,
        "confidence": round(confidence, 2)
    })


@app.route("/clear", methods=["POST", "OPTIONS"])
def clear():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    global index, document_store, image_cache
    index          = faiss.IndexFlatL2(EMBED_DIM)
    document_store = []
    image_cache    = {}
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    logger.info("RAG Visual Chatbot v8 starting...")
    logger.info(f"Models available: {get_available_models()}")
    logger.info(f"Web search: {'enabled' if DDGS else 'disabled — run: pip install ddgs'}")
    app.run(host="localhost", port=5000, debug=False)
          # 🌿 Visual RAG Chatbot — Browser Extension

> An intelligent browser extension that understands images on any webpage using a fully local, offline-capable AI pipeline. Ask questions about anything you see — people, products, art, text in images — and get grounded, web-augmented answers in real time.

---

## Overview

Visual RAG Chatbot is a Chrome extension backed by a local Python server that implements a full **Retrieval-Augmented Generation (RAG)** pipeline for visual question answering. Unlike cloud-based tools, every model runs on your own machine — no API keys, no data sent to third parties, no usage limits.

The extension floats on any webpage. Hover over an image, click **Analyse**, and the system indexes the image's visual content, surrounding page text, and live web search results into a vector database. Every follow-up question retrieves the most relevant chunks and feeds them to a local LLM for a specific, grounded answer.

---

## Demo

> Analyze a news article photo → Ask "Who is this person?" → Get their name, background, and recent news
>
> Analyze a Pinterest fashion pin → Ask "Describe this outfit" → Get detailed description with style notes
>
> Analyze a product page → Ask "What are the key features?" → Get answer from page text + web

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CHROME EXTENSION                         │
│  content.js → detects images, renders chatbot UI           │
│  background.js → service worker, proxies API calls         │
│  chatbot.css → olive-green editorial design theme          │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (localhost:5000)
┌──────────────────────────▼──────────────────────────────────┐
│                    FLASK BACKEND                            │
│                                                             │
│  /process-image  ──►  INDEX PHASE                         │
│    ├── Vision Model (moondream) → image description        │
│    ├── Page Scraper (BeautifulSoup) → alt text, captions   │
│    ├── DuckDuckGo Search → web knowledge                   │
│    └── All text → embedded → stored in FAISS              │
│                                                             │
│  /chat  ──►  RETRIEVE + GENERATE PHASE                    │
│    ├── Query → embedded → FAISS similarity search          │
│    ├── Top-k chunks retrieved (with image-context boost)   │
│    ├── Live web search (for identify/factual queries)      │
│    └── LLM (llama3.2) → grounded answer + confidence      │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### AI / ML
| Component | Technology | Purpose |
|-----------|-----------|---------|
| Image Understanding | **moondream** (via Ollama) | Converts image → detailed text description |
| Text Embeddings | **sentence-transformers** (`all-MiniLM-L6-v2`) | Embeds text chunks into 384-dim vectors |
| Vector Search | **FAISS** (Facebook AI) | Approximate nearest-neighbor retrieval |
| Language Model | **Llama 3.2** (via Ollama) | Generates grounded answers from context |
| RAG Pipeline | Custom implementation | Index → Retrieve → Generate |

### Backend
| Component | Technology |
|-----------|-----------|
| API Server | **Flask** + Flask-CORS |
| Web Scraping | **BeautifulSoup4** |
| Web Search | **DuckDuckGo Search** (ddgs) — free, no API key |
| Image Processing | **Pillow** |
| LLM Runtime | **Ollama** (local model server) |

### Frontend (Chrome Extension)
| Component | Technology |
|-----------|-----------|
| Extension | Chrome Manifest V3 |
| UI Injection | Vanilla JavaScript content script |
| Styling | Custom CSS — olive/forest green editorial theme |
| Typography | DM Sans + Playfair Display (Google Fonts) |
| Background Proxy | Service worker (bypasses Chrome CORS restrictions) |

---

## RAG Pipeline — How It Works

### Phase 1: Indexing (when you click Analyse)

```
Image URL
   │
   ├─► moondream vision model → detailed description
   │
   ├─► BeautifulSoup page scraper
   │     ├── image alt text
   │     ├── figcaption
   │     ├── H1 / product name
   │     ├── surrounding text (3 siblings each direction)
   │     └── full page text → chunked (200 words, 30 overlap)
   │
   ├─► DuckDuckGo search on best available topic
   │     (priority: H1 > alt text > figcaption > title > caption)
   │
   └─► All text → sentence-transformers → 384-dim vectors → FAISS
```

### Phase 2: Retrieval (on each question)

```
User query
   │
   ├─► sentence-transformers → query vector
   │
   ├─► FAISS L2 search → top-14 candidates
   │
   ├─► Re-rank: boost chunks from current image (score × 0.65)
   │
   └─► Top-7 chunks returned, grouped by type:
         vision_description / alt_text / figcaption /
         page_names / web_search / page_content
```

### Phase 3: Generation

```
Retrieved chunks (structured by type)
   +
Query classification: describe / identify / factual / visual_detail / general
   +
Live web search (for identify/factual queries only)
   │
   └─► Llama 3.2 with task-specific prompt → answer + confidence score
```

---

## Features

- **Fully local** — all models run on your machine, nothing sent to external APIs
- **Free and unlimited** — no API keys, no rate limits, no cost
- **Any webpage** — works on Pinterest, Google, Wikipedia, news sites, e-commerce
- **Smart query routing** — detects whether you're asking to describe, identify, get facts, or examine visual details
- **Context boosting** — chunks from the currently-analyzed image are prioritized in retrieval
- **Confidence scoring** — each answer shows a confidence bar based on retrieved context quality
- **Source attribution** — shows which sources (vision, page context, web) contributed to the answer
- **Live web search** — for people/fact identification, runs a fresh DuckDuckGo search
- **Session memory** — FAISS index persists for the browser session; analyze multiple images and ask cross-image questions

---

## Local Setup

### Prerequisites
- Python 3.10+
- Google Chrome
- 6GB free disk space
- 8GB RAM recommended

### 1. Install Ollama and models
```bash
# Install Ollama
# Linux/Mac:
curl -fsSL https://ollama.com/install.sh | sh
# Windows: download from https://ollama.com/download

# Pull required models
ollama pull llama3.2        # ~2GB — language model
ollama pull moondream       # ~1.8GB — vision model
```

### 2. Install Python dependencies
```bash
cd backend
python -m venv venv

# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Start the backend
```bash
python app.py
# → Running on http://localhost:5000
```

### 4. Load Chrome extension
1. Open `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `extension/` folder

### 5. One-time Chrome flag (required for localhost access)
Visit `chrome://flags/#block-insecure-private-network-requests` → set to **Disabled** → Relaunch

---

## Project Structure

```
visual-rag-chatbot/
├── backend/
│   ├── app.py              # Flask server — full RAG pipeline
│   └── requirements.txt    # Python dependencies
├── extension/
│   ├── manifest.json       # Chrome extension config (Manifest V3)
│   ├── content.js          # Injected UI + chatbot logic
│   ├── chatbot.css         # Olive-green editorial design
│   ├── background.js       # Service worker / API proxy
│   ├── icons/              # Extension icons
│   └── popup/
│       ├── popup.html      # Extension toolbar popup
│       └── popup.js        # Status checker
└── README.md
```

---

## NLP / AI Concepts Demonstrated

- **Retrieval-Augmented Generation (RAG)** — grounding LLM responses in retrieved evidence
- **Dense retrieval** — semantic search via sentence embeddings (not keyword matching)
- **Approximate nearest-neighbor search** — FAISS IndexFlatL2
- **Text chunking with overlap** — sliding window chunking for better recall
- **Multi-modal pipeline** — vision model + text embeddings + LLM working together
- **Query classification** — routing questions to appropriate retrieval/generation strategies
- **Relevance boosting** — re-ranking retrieved chunks by metadata (current image context)
- **Prompt engineering** — task-specific system prompts per query type
- **Web-augmented RAG** — live web search results indexed alongside static context

---

## Requirements

```
flask
flask-cors
requests
Pillow
transformers
sentence-transformers
faiss-cpu
ollama
beautifulsoup4
numpy
torch
ddgs
```

---

## Notes

- Models download automatically on first run from HuggingFace (cached locally after)
- FAISS index is in-memory; cleared on server restart or when user clicks the reset button
- The extension requires the Flask backend to be running locally
- Tested on Chrome 120+; should work on any Chromium-based browser

---

## License

MIT
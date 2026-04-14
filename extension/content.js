/**
 * content.js — RAG Visual Chatbot v8
 * Olive-green organic design, works with app.py v8
 */

let currentImageUrl = null;
let isProcessing    = false;

// ── Backend proxy through service worker ─────────────────────────────────────
function backendFetch(url, method = "GET", body = null) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      { type: "FETCH", url, method, body },
      (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        if (!response)            { reject(new Error("No response from background")); return; }
        if (response.error)       { reject(new Error(response.error)); return; }
        resolve(response);
      }
    );
  });
}

// ── Build UI ──────────────────────────────────────────────────────────────────
function buildChatbot() {
  if (document.getElementById("vis-root")) return;

  const root = document.createElement("div");
  root.id = "vis-root";
  root.innerHTML = `
    <div id="vis-fab" title="Visual RAG Assistant">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" fill="currentColor" opacity="0.15"/>
        <path d="M9.5 9a2.5 2.5 0 1 1 5 0 2.5 2.5 0 0 1-5 0z" fill="currentColor"/>
        <path d="M5 19c0-3.31 3.13-6 7-6s7 2.69 7 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
    </div>

    <div id="vis-panel" class="vis-hidden">

      <div id="vis-header">
        <div id="vis-header-left">
          <div id="vis-avatar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="8" r="4" fill="currentColor"/>
              <path d="M4 20c0-4 3.58-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div id="vis-header-info">
            <span id="vis-name">Visual Assistant</span>
            <span id="vis-status-text">
              <span id="vis-status-dot"></span>
              <span id="vis-status-label">Connecting...</span>
            </span>
          </div>
        </div>
        <div id="vis-header-actions">
          <button id="vis-clear-btn" title="New session">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              <path d="M3 3v5h5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <button id="vis-close-btn" title="Close">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      </div>

      <div id="vis-image-zone">
        <div id="vis-hint">
          <div id="vis-hint-icon">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="1.5"/>
              <circle cx="8.5" cy="8.5" r="1.5" fill="currentColor"/>
              <path d="M21 15l-5-5L5 21" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <p>Hover over any image on the page<br/>and click <strong>Analyse</strong></p>
        </div>
        <div id="vis-image-card" class="vis-hidden">
          <img id="vis-thumb" src="" alt=""/>
          <div id="vis-image-meta">
            <span class="vis-chip">Analysed</span>
            <p id="vis-caption-text"></p>
          </div>
        </div>
      </div>

      <div id="vis-messages"></div>

      <div id="vis-input-row">
        <textarea
          id="vis-input"
          placeholder="Ask anything about this image…"
          rows="1"
          autocomplete="off"
          spellcheck="false"
        ></textarea>
        <button id="vis-send-btn" disabled>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M22 2L11 13M22 2L15 22 11 13 2 9 22 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>

    </div>

    <div id="vis-tooltip" class="vis-hidden">
      <button id="vis-analyse-btn">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="8" stroke="currentColor" stroke-width="2"/>
          <path d="m21 21-4.35-4.35" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        Analyse
      </button>
    </div>
  `;

  document.body.appendChild(root);
  attachEvents();
  checkHealth();
}

// ── Events ────────────────────────────────────────────────────────────────────
function attachEvents() {
  const fab        = document.getElementById("vis-fab");
  const panel      = document.getElementById("vis-panel");
  const closeBtn   = document.getElementById("vis-close-btn");
  const clearBtn   = document.getElementById("vis-clear-btn");
  const sendBtn    = document.getElementById("vis-send-btn");
  const input      = document.getElementById("vis-input");
  const tooltip    = document.getElementById("vis-tooltip");
  const analyseBtn = document.getElementById("vis-analyse-btn");

  fab.addEventListener("click", () => {
    const open = !panel.classList.contains("vis-hidden");
    panel.classList.toggle("vis-hidden");
    fab.classList.toggle("vis-open", !open);
  });

  closeBtn.addEventListener("click", () => {
    panel.classList.add("vis-hidden");
    fab.classList.remove("vis-open");
  });

  clearBtn.addEventListener("click", async () => {
    try { await backendFetch("/clear", "POST"); } catch(e) {}
    currentImageUrl = null;
    document.getElementById("vis-messages").innerHTML = "";
    document.getElementById("vis-image-card").classList.add("vis-hidden");
    document.getElementById("vis-hint").classList.remove("vis-hidden");
    document.getElementById("vis-send-btn").disabled = true;
    addSystem("Session cleared. Hover over an image to begin.");
  });

  // Send
  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  // Enable send when there's text
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 100) + "px";
    sendBtn.disabled = !input.value.trim() || isProcessing;
  });

  // Hover detection
  document.addEventListener("mouseover", (e) => {
    const img = e.target.closest("img");
    if (!img || img.id === "vis-thumb") return;
    const src = img.src || "";
    if (!src.startsWith("http") || src.includes(".svg") ||
        img.naturalWidth < 60 || img.naturalHeight < 60) return;

    const rect = img.getBoundingClientRect();
    tooltip.style.top  = `${window.scrollY + rect.top + 6}px`;
    tooltip.style.left = `${window.scrollX + rect.left + 6}px`;
    tooltip.classList.remove("vis-hidden");
    tooltip.dataset.src = src;
  });

  document.addEventListener("mouseout", (e) => {
    if (!tooltip.contains(e.relatedTarget) && e.relatedTarget !== tooltip) {
      tooltip.classList.add("vis-hidden");
    }
  });

  tooltip.addEventListener("mouseleave", () => tooltip.classList.add("vis-hidden"));

  analyseBtn.addEventListener("click", () => {
    const src = tooltip.dataset.src;
    tooltip.classList.add("vis-hidden");
    if (src) analyseImage(src);
  });
}

// ── Health check ──────────────────────────────────────────────────────────────
async function checkHealth() {
  const dot   = document.getElementById("vis-status-dot");
  const label = document.getElementById("vis-status-label");
  try {
    const res = await backendFetch("/health");
    if (res.ok && res.data?.status === "ok") {
      dot.classList.add("vis-online");
      label.textContent = "Online";
    } else throw new Error();
  } catch {
    dot.classList.add("vis-offline");
    label.textContent = "Offline";
    addSystem("Backend offline. Run: cd backend && venv\\Scripts\\activate && python app.py");
  }
}

// ── Analyse image ─────────────────────────────────────────────────────────────
async function analyseImage(src) {
  currentImageUrl = src;

  // Open panel
  document.getElementById("vis-panel").classList.remove("vis-hidden");
  document.getElementById("vis-fab").classList.add("vis-open");

  // Show image card
  document.getElementById("vis-hint").classList.add("vis-hidden");
  document.getElementById("vis-image-card").classList.remove("vis-hidden");
  document.getElementById("vis-thumb").src = src;
  document.getElementById("vis-caption-text").textContent = "Analysing…";

  addSystem(`Analysing image…`);

  try {
    const res = await backendFetch("/process-image", "POST", {
      image_url:  src,
      page_url:   window.location.href,
      page_title: document.title
    });

    if (res.ok && res.data) {
      const cap = res.data.caption || "";
      document.getElementById("vis-caption-text").textContent =
        cap.length > 100 ? cap.substring(0, 100) + "…" : (cap || "Ready to answer questions.");

      document.getElementById("vis-send-btn").disabled = false;
      addSystem("✓ Image indexed. Ask me anything about it.");
    } else {
      document.getElementById("vis-caption-text").textContent = "Could not analyse.";
    }
  } catch (err) {
    document.getElementById("vis-caption-text").textContent = "Connection error.";
    addSystem(`Error: ${err.message}`);
  }
}

// ── Send message ──────────────────────────────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById("vis-input");
  const query = input.value.trim();
  if (!query || isProcessing) return;

  isProcessing = true;
  input.value  = "";
  input.style.height = "auto";
  document.getElementById("vis-send-btn").disabled = true;

  addUserBubble(query);
  const typingId = addAssistantBubble("", true);

  try {
    const res = await backendFetch("/chat", "POST", {
      query,
      image_url: currentImageUrl,
      page_url:  window.location.href
    });

    if (res.ok && res.data) {
      const { answer, sources, confidence } = res.data;
      updateBubble(typingId, answer || "No response.");

      if (sources && sources.length > 0) {
        addMeta(typingId, sources, confidence);
      }
    } else {
      updateBubble(typingId, "No response received.");
    }
  } catch (err) {
    updateBubble(typingId, `Connection error: ${err.message}`);
  }

  isProcessing = false;
  document.getElementById("vis-send-btn").disabled = !document.getElementById("vis-input").value.trim();
}

// ── UI helpers ────────────────────────────────────────────────────────────────
function addUserBubble(text) {
  const msgs = document.getElementById("vis-messages");
  const wrap = document.createElement("div");
  wrap.className = "vis-msg-wrap vis-user-wrap";
  wrap.innerHTML = `<div class="vis-bubble vis-user-bubble">${escapeHtml(text)}</div>`;
  msgs.appendChild(wrap);
  msgs.scrollTop = msgs.scrollHeight;
}

function addAssistantBubble(text, typing = false) {
  const msgs = document.getElementById("vis-messages");
  const id   = "vm-" + Date.now();
  const wrap = document.createElement("div");
  wrap.className = "vis-msg-wrap vis-bot-wrap";
  wrap.id = id + "-wrap";
  wrap.innerHTML = typing
    ? `<div class="vis-bubble vis-bot-bubble" id="${id}">
         <span class="vis-typing"><span></span><span></span><span></span></span>
       </div>`
    : `<div class="vis-bubble vis-bot-bubble" id="${id}">${escapeHtml(text)}</div>`;
  msgs.appendChild(wrap);
  msgs.scrollTop = msgs.scrollHeight;
  return id;
}

function updateBubble(id, text) {
  const el = document.getElementById(id);
  if (el) {
    el.textContent = text;
    document.getElementById("vis-messages").scrollTop = 9999;
  }
}

function addMeta(bubbleId, sources, confidence) {
  const wrap = document.getElementById(bubbleId + "-wrap");
  if (!wrap) return;
  const meta = document.createElement("div");
  meta.className = "vis-meta";

  if (confidence !== undefined) {
    const pct = Math.round(confidence * 100);
    meta.innerHTML = `
      <span class="vis-conf-bar">
        <span class="vis-conf-fill" style="width:${pct}%"></span>
      </span>
      <span class="vis-meta-text">${pct}% confidence · ${sources.join(", ")}</span>
    `;
  } else {
    meta.innerHTML = `<span class="vis-meta-text">Sources: ${sources.join(", ")}</span>`;
  }
  wrap.appendChild(meta);
}

function addSystem(text) {
  const msgs = document.getElementById("vis-messages");
  const div  = document.createElement("div");
  div.className = "vis-system";
  div.textContent = text;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/\n/g, "<br>");
}

buildChatbot();
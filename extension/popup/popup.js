const BACKEND = "http://localhost:5000";

async function checkStatus() {
  const statusEl = document.getElementById("backend-status");
  const countEl  = document.getElementById("doc-count");

  statusEl.textContent = "Checking...";
  statusEl.className = "badge badge-checking";

  try {
    const res  = await fetch(`${BACKEND}/health`);
    const data = await res.json();
    statusEl.textContent = "Online ✓";
    statusEl.className = "badge badge-online";
    countEl.textContent = `${data.indexed_docs} chunks`;
    countEl.className = "badge badge-online";
  } catch {
    statusEl.textContent = "Offline ✗";
    statusEl.className = "badge badge-offline";
    countEl.textContent = "—";
    countEl.className = "badge badge-offline";
  }
}

document.getElementById("check-btn").addEventListener("click", checkStatus);
checkStatus();

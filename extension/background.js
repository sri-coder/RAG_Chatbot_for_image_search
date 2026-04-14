/**
 * background.js — Service Worker
 * Proxies all fetch calls from content.js to the Flask backend.
 * Service workers are not subject to Chrome's Private Network Access
 * restrictions that block content scripts from calling localhost.
 */

const BACKEND = "http://localhost:5000";

chrome.runtime.onInstalled.addListener(() => {
  console.log("RAG Visual Chatbot installed.");
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "FETCH") {
    handleFetch(message)
      .then(sendResponse)
      .catch(err => sendResponse({ ok: false, error: err.message }));
    return true; // Keep channel open for async response
  }
  if (message.type === "PING") {
    sendResponse({ status: "alive" });
  }
  return true;
});

async function handleFetch({ url, method = "GET", body = null }) {
  try {
    const options = {
      method,
      headers: { "Content-Type": "application/json" },
    };
    if (body && method !== "GET") {
      options.body = JSON.stringify(body);
    }

    const res = await fetch(`${BACKEND}${url}`, options);
    const data = await res.json();
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    console.error("Backend fetch error:", err.message);
    return { ok: false, error: err.message };
  }
}

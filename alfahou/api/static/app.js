const API_BASE = window.ALFAHOU_API || "https://alfahou.onrender.com";

const form = document.getElementById("composer");
const promptEl = document.getElementById("prompt");
const statusEl = document.getElementById("status");
const threadEl = document.getElementById("thread");
const goBtn = document.getElementById("go");
const deviceEl = document.getElementById("device");

function apiUrl(path) {
  return `${API_BASE}${path}`;
}

function assetUrl(path) {
  if (!path) return path;
  if (path.startsWith("http")) return path;
  return apiUrl(path);
}

function autoSize() {
  promptEl.style.height = "auto";
  promptEl.style.height = `${Math.min(promptEl.scrollHeight, 140)}px`;
}

promptEl.addEventListener("input", autoSize);

promptEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

async function refreshHealth() {
  try {
    const res = await fetch(apiUrl("/api/health"));
    const data = await res.json();
    deviceEl.textContent = `${data.device} · en ligne`;
  } catch {
    deviceEl.textContent = "hors ligne";
  }
}

function setStatus(msg, isError = false) {
  statusEl.hidden = !msg;
  statusEl.textContent = msg || "";
  statusEl.classList.toggle("error", isError);
}

function clearExchange() {
  threadEl.querySelectorAll(".bubble:not(.welcome)").forEach((el) => el.remove());
  const welcome = document.getElementById("welcome");
  if (welcome) welcome.hidden = true;
}

function addBubble({ role, html, text }) {
  const el = document.createElement("article");
  el.className = `bubble ${role === "you" ? "you" : "bot"}`;
  const who = document.createElement("p");
  who.className = "who";
  who.textContent = role === "you" ? "Toi" : "AlfAhou";
  el.appendChild(who);
  if (html) {
    const body = document.createElement("div");
    body.innerHTML = html;
    el.appendChild(body);
  } else {
    const p = document.createElement("p");
    p.textContent = text || "";
    el.appendChild(p);
  }
  threadEl.appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
  return el;
}

function addTyping() {
  const el = document.createElement("article");
  el.className = "bubble bot typing";
  el.id = "typing";
  el.innerHTML = `<p class="who">AlfAhou</p><p class="dots" aria-label="écrit"><i></i><i></i><i></i></p>`;
  threadEl.appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
  return el;
}

function removeTyping() {
  document.getElementById("typing")?.remove();
}

function renderReply(data) {
  removeTyping();
  const parts = [];
  if (data.text) {
    parts.push(`<p>${escapeHtml(data.text).replace(/\n/g, "<br>")}</p>`);
  }
  if (data.file_url) {
    const url = assetUrl(data.file_url);
    if (data.modality === "image" || url.endsWith(".png") || url.endsWith(".jpg")) {
      parts.push(`<img src="${url}" alt="Image générée par AlfAhou" />`);
    } else if (data.modality === "video" || url.endsWith(".mp4")) {
      parts.push(`<video src="${url}" controls autoplay loop></video>`);
    }
    parts.push(`<p class="meta"><a href="${url}" download target="_blank" rel="noopener">Télécharger</a></p>`);
  }
  if (!parts.length) {
    parts.push("<p>Voilà.</p>");
  }
  addBubble({ role: "bot", html: parts.join("") });
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = promptEl.value.trim();
  if (!prompt) return;
  const modality = form.querySelector('input[name="modality"]:checked').value;

  clearExchange();
  addBubble({ role: "you", text: prompt });
  promptEl.value = "";
  autoSize();
  goBtn.disabled = true;
  setStatus("");
  addTyping();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);

  try {
    const res = await fetch(apiUrl("/api/generate"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        modality,
        max_tokens: modality === "text" || modality === "pdf" || modality === "auto" ? 120 : 40,
      }),
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail || data.message || `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    renderReply(data);
  } catch (err) {
    removeTyping();
    const msg =
      err && err.name === "AbortError"
        ? "Toujours en route… Réessaie dans un instant."
        : (err && err.message) || "Je n’ai pas pu répondre.";
    addBubble({ role: "bot", text: msg });
    setStatus(msg, true);
  } finally {
    clearTimeout(timeout);
    goBtn.disabled = false;
    promptEl.focus();
  }
});

refreshHealth();
promptEl.focus();

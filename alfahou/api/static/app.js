const API_BASE = window.ALFAHOU_API || "https://alfahou.onrender.com";

const form = document.getElementById("composer");
const promptEl = document.getElementById("prompt");
const statusEl = document.getElementById("status");
const threadEl = document.getElementById("thread");
const goBtn = document.getElementById("go");
const modeEl = document.getElementById("mode");
const suggestionsEl = document.getElementById("suggestions");
const deviceEl = document.getElementById("device");
const btnReset = document.getElementById("btn-reset");
const btnResetM = document.getElementById("btn-reset-m");
const btnMic = document.getElementById("btn-mic");
const btnVoiceOut = document.getElementById("btn-voice-out");

let sessionId = localStorage.getItem("alfahou_session") || null;
let lastBotText = "";
let speakReplies = localStorage.getItem("alfahou_speak") === "1";
if (speakReplies) btnVoiceOut.classList.add("listening");

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
  promptEl.style.height = `${Math.min(promptEl.scrollHeight, 144)}px`;
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
    if (deviceEl) deviceEl.textContent = `${data.device} · en ligne`;
  } catch {
    if (deviceEl) deviceEl.textContent = "hors ligne";
  }
}

function setStatus(msg) {
  statusEl.hidden = !msg;
  statusEl.textContent = msg || "";
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, _l, code) => `<pre><code>${code.trim()}</code></pre>`);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/^(?:- |\* )(.+)$/gm, "<li>$1</li>");
  html = html.replace(/(?:^|\n)(\d+)\. (.+)$/gm, "<li>$2</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");
  return `<p>${html}</p>`;
}

function addMessage({ role, text, fileUrl, modality }) {
  const el = document.createElement("article");
  el.className = `msg ${role === "you" ? "you" : "bot"}`;

  const label = document.createElement("p");
  label.className = "msg-label";
  label.textContent = role === "you" ? "Toi" : "AlfAhou";
  el.appendChild(label);

  if (role === "you") {
    const body = document.createElement("div");
    body.textContent = text || "";
    el.appendChild(body);
  } else {
    const body = document.createElement("div");
    body.className = "md";
    body.innerHTML = renderMarkdown(text || "");
    el.appendChild(body);
    if (fileUrl) {
      const url = assetUrl(fileUrl);
      if (modality === "image" || url.endsWith(".png") || url.endsWith(".jpg")) {
        const img = document.createElement("img");
        img.src = url;
        img.alt = "Image AlfAhou";
        el.appendChild(img);
      } else if (modality === "video" || url.endsWith(".mp4")) {
        const vid = document.createElement("video");
        vid.src = url;
        vid.controls = true;
        vid.autoplay = true;
        vid.loop = true;
        el.appendChild(vid);
      }
      const meta = document.createElement("p");
      meta.className = "meta";
      meta.innerHTML = `<a href="${url}" download target="_blank" rel="noopener">Télécharger</a>`;
      el.appendChild(meta);
    }
  }

  threadEl.appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
  return el;
}

function addTyping() {
  const el = document.createElement("article");
  el.className = "msg bot typing";
  el.id = "typing";
  el.innerHTML = `<i></i><i></i><i></i>`;
  threadEl.appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
}

function removeTyping() {
  document.getElementById("typing")?.remove();
}

function showSuggestions(items) {
  suggestionsEl.innerHTML = "";
  if (!items || !items.length) {
    suggestionsEl.hidden = true;
    return;
  }
  suggestionsEl.hidden = false;
  items.forEach((label) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.addEventListener("click", () => {
      promptEl.value = label;
      autoSize();
      form.requestSubmit();
    });
    suggestionsEl.appendChild(b);
  });
}

function speak(text) {
  if (!speakReplies || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text.slice(0, 600));
  u.lang = /[éèàùç]/i.test(text) ? "fr-FR" : "en-US";
  window.speechSynthesis.speak(u);
}

btnVoiceOut.addEventListener("click", () => {
  speakReplies = !speakReplies;
  localStorage.setItem("alfahou_speak", speakReplies ? "1" : "0");
  btnVoiceOut.classList.toggle("listening", speakReplies);
  if (speakReplies && lastBotText) speak(lastBotText);
  else window.speechSynthesis?.cancel();
});

async function resetChat() {
  if (sessionId) {
    try {
      await fetch(apiUrl("/api/chat/reset"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
    } catch {}
  }
  sessionId = null;
  localStorage.removeItem("alfahou_session");
  threadEl.innerHTML = "";
  addMessage({
    role: "bot",
    text: "Nouvelle conversation. Dis-moi ce que tu veux créer ou comprendre.",
  });
  showSuggestions(["Bonjour", "Que sais-tu faire ?", "Fais un plan"]);
  setStatus("");
}

btnReset?.addEventListener("click", resetChat);
btnResetM?.addEventListener("click", resetChat);

let recognition = null;
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = "fr-FR";
  recognition.interimResults = false;
  recognition.onresult = (ev) => {
    const said = ev.results[0][0].transcript;
    promptEl.value = (promptEl.value ? promptEl.value + " " : "") + said;
    autoSize();
  };
  recognition.onend = () => btnMic.classList.remove("listening");
}
btnMic.addEventListener("click", () => {
  if (!recognition) {
    setStatus("Dictée non supportée sur ce navigateur.");
    return;
  }
  btnMic.classList.add("listening");
  recognition.start();
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = promptEl.value.trim();
  if (!prompt) return;
  const modality = form.querySelector('input[name="modality"]:checked').value;
  const mode = modeEl.value;

  addMessage({ role: "you", text: prompt });
  promptEl.value = "";
  autoSize();
  goBtn.disabled = true;
  setStatus("");
  showSuggestions([]);
  addTyping();

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 120000);

  try {
    const res = await fetch(apiUrl("/api/chat"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        session_id: sessionId,
        modality,
        mode,
      }),
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || `HTTP ${res.status}`);
    sessionId = data.session_id;
    localStorage.setItem("alfahou_session", sessionId);
    removeTyping();
    lastBotText = data.text || "";
    addMessage({
      role: "bot",
      text: data.text,
      fileUrl: data.file_url,
      modality: data.modality,
    });
    showSuggestions(data.suggestions || []);
    speak(lastBotText);
  } catch (err) {
    removeTyping();
    const msg =
      err && err.name === "AbortError"
        ? "Toujours en route… réessaie."
        : (err && err.message) || "Je n’ai pas pu répondre.";
    addMessage({ role: "bot", text: msg });
    setStatus(msg);
  } finally {
    clearTimeout(timeout);
    goBtn.disabled = false;
    promptEl.focus();
  }
});

refreshHealth();
showSuggestions(["Bonjour", "Que sais-tu faire ?", "Explique l’IA"]);
promptEl.focus();

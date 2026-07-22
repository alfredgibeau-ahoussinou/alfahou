const API_BASE = window.ALFAHOU_API || "https://alfahou.onrender.com";

const form = document.getElementById("composer");
const promptEl = document.getElementById("prompt");
const statusEl = document.getElementById("status");
const threadEl = document.getElementById("thread");
const goBtn = document.getElementById("go");
const deviceEl = document.getElementById("device");
const modeEl = document.getElementById("mode");
const suggestionsEl = document.getElementById("suggestions");
const btnReset = document.getElementById("btn-reset");
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
    const caps = (data.models && data.models.capabilities) || [];
    deviceEl.textContent = `${data.device} · ${caps.length || "ok"} skills`;
  } catch {
    deviceEl.textContent = "hors ligne";
  }
}

function setStatus(msg, isError = false) {
  statusEl.hidden = !msg;
  statusEl.textContent = msg || "";
  statusEl.classList.toggle("error", isError);
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
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (_, _lang, code) => `<pre><code>${code.trim()}</code></pre>`);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/^(?:- |\* )(.+)$/gm, "<li>$1</li>");
  html = html.replace(/(?:^|\n)(\d+)\. (.+)$/gm, "<li>$2</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`);
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");
  return `<p>${html}</p>`;
}

function addBubble({ role, text, html, fileUrl, modality }) {
  const el = document.createElement("article");
  el.className = `bubble ${role === "you" ? "you" : "bot"}`;
  const who = document.createElement("p");
  who.className = "who";
  who.textContent = role === "you" ? "Toi" : "AlfAhou";
  el.appendChild(who);

  if (role === "you") {
    const p = document.createElement("p");
    p.textContent = text || "";
    el.appendChild(p);
  } else {
    const body = document.createElement("div");
    body.className = "md";
    body.innerHTML = html || renderMarkdown(text || "");
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
  el.className = "bubble bot typing";
  el.id = "typing";
  el.innerHTML = `<p class="who">AlfAhou</p><p class="dots"><i></i><i></i><i></i></p>`;
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

btnReset.addEventListener("click", async () => {
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
  addBubble({
    role: "bot",
    text: "Nouvelle conversation. Dis-moi ce que tu veux — texte, image, plan, code, PDF…",
  });
  showSuggestions(["Bonjour", "Que sais-tu faire ?", "Fais un plan"]);
  setStatus("");
});

// Dictée (Web Speech API navigateur)
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
    setStatus("Dictée non supportée sur ce navigateur.", true);
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

  addBubble({ role: "you", text: prompt });
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
    if (!res.ok) {
      throw new Error(data.detail || data.message || `HTTP ${res.status}`);
    }
    sessionId = data.session_id;
    localStorage.setItem("alfahou_session", sessionId);
    removeTyping();
    lastBotText = data.text || "";
    addBubble({
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
    addBubble({ role: "bot", text: msg });
    setStatus(msg, true);
  } finally {
    clearTimeout(timeout);
    goBtn.disabled = false;
    promptEl.focus();
  }
});

refreshHealth();
showSuggestions(["Bonjour", "Que sais-tu faire ?", "Explique l’IA simplement"]);
promptEl.focus();

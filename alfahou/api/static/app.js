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
const btnMic = document.getElementById("btn-mic");
const btnVoiceOut = document.getElementById("btn-voice-out");
const cursor = document.getElementById("cursor");

let sessionId = localStorage.getItem("alfahou_session") || null;
let lastBotText = "";
let speakReplies = localStorage.getItem("alfahou_speak") === "1";
if (speakReplies) btnVoiceOut?.classList.add("listening");

const isTouch =
  window.matchMedia("(pointer: coarse)").matches ||
  "ontouchstart" in window ||
  navigator.maxTouchPoints > 0;
if (isTouch) document.body.classList.add("touch-device");

/* —— Routing multi-vues —— */
const views = {
  intro: document.getElementById("view-intro"),
  manifest: document.getElementById("view-manifest"),
  studio: document.getElementById("view-studio"),
};

function go(name, { push = true } = {}) {
  const key = views[name] ? name : "intro";
  Object.entries(views).forEach(([k, el]) => {
    if (!el) return;
    const on = k === key;
    el.hidden = !on;
    if (on) {
      el.removeAttribute("hidden");
      // reflow for animation
      void el.offsetWidth;
    }
  });
  document.body.dataset.view = key;
  if (push) {
    const hash = key === "intro" ? "" : `#${key}`;
    if (location.hash.replace("#", "") !== (key === "intro" ? "" : key)) {
      history.pushState({ view: key }, "", hash || location.pathname);
    }
  }
  if (key === "studio") {
    setTimeout(() => promptEl?.focus(), 350);
  }
  window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
}

function viewFromHash() {
  const h = (location.hash || "").replace("#", "");
  if (h === "studio" || h === "manifest") return h;
  return "intro";
}

document.querySelectorAll("[data-go]").forEach((el) => {
  el.addEventListener("click", (e) => {
    e.preventDefault();
    go(el.getAttribute("data-go"));
  });
});
window.addEventListener("popstate", () => go(viewFromHash(), { push: false }));
go(viewFromHash(), { push: false });

/* —— Curseur custom —— */
if (cursor && !isTouch && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  let x = window.innerWidth / 2;
  let y = window.innerHeight / 2;
  let cx = x;
  let cy = y;
  window.addEventListener("pointermove", (e) => {
    x = e.clientX;
    y = e.clientY;
  });
  const tick = () => {
    cx += (x - cx) * 0.22;
    cy += (y - cy) * 0.22;
    cursor.style.transform = `translate3d(${cx}px, ${cy}px, 0)`;
    requestAnimationFrame(tick);
  };
  tick();

  const hoverSel = "a, button, label, select, textarea, .m-card, [data-go]";
  document.addEventListener("pointerover", (e) => {
    if (e.target.closest(hoverSel)) cursor.classList.add("hover");
  });
  document.addEventListener("pointerout", (e) => {
    if (e.target.closest(hoverSel)) cursor.classList.remove("hover");
  });
}

/* —— Boutons magnétiques —— */
document.querySelectorAll(".btn-magnetic").forEach((btn) => {
  btn.addEventListener("pointermove", (e) => {
    if (isTouch) return;
    const r = btn.getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
    btn.style.transform = `translate(${dx * 6}px, ${dy * 5}px)`;
  });
  btn.addEventListener("pointerleave", () => {
    btn.style.transform = "";
  });
});

/* —— Cards tilt manifeste —— */
document.querySelectorAll("[data-tilt]").forEach((card) => {
  card.addEventListener("pointermove", (e) => {
    if (isTouch) return;
    const r = card.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    card.style.transform = `perspective(700px) rotateY(${px * 7}deg) rotateX(${-py * 7}deg) translateY(-2px)`;
  });
  card.addEventListener("pointerleave", () => {
    card.style.transform = "";
  });
});

/* —— Chat —— */
function apiUrl(path) {
  return `${API_BASE}${path}`;
}
function assetUrl(path) {
  if (!path) return path;
  if (path.startsWith("http")) return path;
  return apiUrl(path);
}
function markBusy() {
  document.body.classList.add("busy");
}
function autoSize() {
  if (!promptEl) return;
  promptEl.style.height = "auto";
  promptEl.style.height = `${Math.min(promptEl.scrollHeight, 136)}px`;
}
promptEl?.addEventListener("input", autoSize);
promptEl?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    form.requestSubmit();
  }
});

async function refreshHealth() {
  if (!deviceEl) return;
  try {
    const res = await fetch(apiUrl("/api/health"));
    const data = await res.json();
    const llm = data.models && data.models.llm;
    const llmBit = llm && llm.enabled ? ` · LLM ${llm.provider || "cloud"}` : " · mode léger";
    deviceEl.textContent = `${data.device} · en ligne${llmBit}`;
  } catch {
    deviceEl.textContent = "hors ligne";
  }
}

function setStatus(msg) {
  if (!statusEl) return;
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

function stamp() {
  return new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function addRow({ role, text, fileUrl, modality }) {
  const el = document.createElement("article");
  el.className = `turn ${role === "you" ? "you" : "bot"}`;

  const head = document.createElement("header");
  head.className = "turn-head";
  head.innerHTML = `<span class="who">${role === "you" ? "Toi" : "AlfAhou"}</span><time class="when">${stamp()}</time>`;
  el.appendChild(head);

  const body = document.createElement("div");
  body.className = "turn-body" + (role === "bot" ? " md" : "");
  if (role === "you") body.textContent = text || "";
  else body.innerHTML = renderMarkdown(text || "");
  el.appendChild(body);

  if (fileUrl && role === "bot") {
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
    const metaFile = document.createElement("p");
    metaFile.className = "file-meta";
    metaFile.innerHTML = `<a href="${url}" download target="_blank" rel="noopener">Télécharger</a>`;
    el.appendChild(metaFile);
  }

  threadEl.appendChild(el);
  markBusy();
  el.scrollIntoView({ behavior: "smooth", block: "end" });
  return el;
}

function addTyping() {
  const el = document.createElement("article");
  el.className = "turn bot typing";
  el.id = "typing";
  el.innerHTML =
    `<header class="turn-head"><span class="who">AlfAhou</span><time class="when">…</time></header>` +
    `<div class="turn-body"><span class="dots"><i></i><i></i><i></i></span></div>`;
  threadEl.appendChild(el);
  el.scrollIntoView({ behavior: "smooth", block: "end" });
}

function removeTyping() {
  document.getElementById("typing")?.remove();
}

function showSuggestions(items) {
  if (!suggestionsEl) return;
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

btnVoiceOut?.addEventListener("click", () => {
  speakReplies = !speakReplies;
  localStorage.setItem("alfahou_speak", speakReplies ? "1" : "0");
  btnVoiceOut.classList.toggle("listening", speakReplies);
  if (speakReplies && lastBotText) speak(lastBotText);
  else window.speechSynthesis?.cancel();
});

btnReset?.addEventListener("click", async () => {
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
  document.body.classList.remove("busy");
  threadEl.innerHTML = "";
  addRow({
    role: "bot",
    text: "Nouveau fil. Dis-moi ce que tu veux créer ou comprendre.",
  });
  document.body.classList.remove("busy");
  threadEl.querySelector(".turn")?.classList.add("welcome");
  showSuggestions(["Bonjour", "Que sais-tu faire ?", "Fais un plan"]);
  setStatus("");
});

let recognition = null;
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = "fr-FR";
  recognition.interimResults = false;
  recognition.onresult = (ev) => {
    promptEl.value = (promptEl.value ? promptEl.value + " " : "") + ev.results[0][0].transcript;
    autoSize();
  };
  recognition.onend = () => btnMic?.classList.remove("listening");
}
btnMic?.addEventListener("click", () => {
  if (!recognition) {
    setStatus("Dictée non supportée sur ce navigateur.");
    return;
  }
  btnMic.classList.add("listening");
  recognition.start();
});

form?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = promptEl.value.trim();
  if (!prompt) return;
  const modalityEl = document.querySelector('input[name="modality"]:checked');
  const modality = modalityEl ? modalityEl.value : "auto";
  const mode = modeEl.value;

  markBusy();
  addRow({ role: "you", text: prompt });
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
      body: JSON.stringify({ prompt, session_id: sessionId, modality, mode }),
      signal: controller.signal,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || `HTTP ${res.status}`);
    sessionId = data.session_id;
    localStorage.setItem("alfahou_session", sessionId);
    removeTyping();
    lastBotText = data.text || "";
    addRow({
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
    addRow({ role: "bot", text: msg });
    setStatus(msg);
  } finally {
    clearTimeout(timeout);
    goBtn.disabled = false;
    promptEl.focus();
  }
});

refreshHealth();
showSuggestions(["Bonjour", "Que sais-tu faire ?", "Explique l’IA"]);

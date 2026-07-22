const form = document.getElementById("studio");
const promptEl = document.getElementById("prompt");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const goBtn = document.getElementById("go");
const deviceEl = document.getElementById("device");

async function refreshHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    const m = data.models || {};
    const ready = [
      m.text ? "texte" : null,
      m.image ? "image" : null,
      m.video ? "vidéo" : null,
      "pdf",
    ].filter(Boolean).join(" · ");
    deviceEl.textContent = `${data.device} · ${ready}`;
  } catch {
    deviceEl.textContent = "hors ligne";
  }
}

function setStatus(msg, isError = false) {
  statusEl.hidden = !msg;
  statusEl.textContent = msg;
  statusEl.classList.toggle("error", isError);
}

function renderResult(data) {
  resultEl.hidden = false;
  resultEl.innerHTML = "";
  const meta = document.createElement("p");
  meta.style.color = "var(--mute)";
  meta.style.margin = "0 0 0.75rem";
  meta.textContent = `Modalité : ${data.modality}`;
  resultEl.appendChild(meta);

  if (data.text) {
    const pre = document.createElement("pre");
    pre.textContent = data.text;
    resultEl.appendChild(pre);
  }

  if (data.file_url) {
    const url = data.file_url;
    if (data.modality === "image" || url.endsWith(".png") || url.endsWith(".jpg")) {
      const img = document.createElement("img");
      img.src = url;
      img.alt = "Image générée par AlfAhou";
      resultEl.appendChild(img);
    } else if (data.modality === "video" || url.endsWith(".mp4")) {
      const vid = document.createElement("video");
      vid.src = url;
      vid.controls = true;
      vid.autoplay = true;
      vid.loop = true;
      resultEl.appendChild(vid);
    }
    const link = document.createElement("p");
    link.innerHTML = `<a href="${url}" download>Télécharger le fichier</a>`;
    resultEl.appendChild(link);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = promptEl.value.trim();
  if (!prompt) return;
  const modality = form.querySelector('input[name="modality"]:checked').value;
  goBtn.disabled = true;
  setStatus("AlfAhou génère…");
  resultEl.hidden = true;

  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, modality, max_tokens: 220 }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Échec de génération");
    setStatus("Terminé.");
    renderResult(data);
  } catch (err) {
    setStatus(err.message || String(err), true);
  } finally {
    goBtn.disabled = false;
  }
});

refreshHealth();

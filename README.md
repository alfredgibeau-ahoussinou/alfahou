# AlfAhou

IA multimédia d’**Alfred Ahoussinou** — chat (LLM open-source cloud), images, vidéos et PDF.

## Production

- **Site** : [https://alfahou.netlify.app](https://alfahou.netlify.app)
- **API** : [https://alfahou.onrender.com](https://alfahou.onrender.com)
- **Code** : [github.com/alfredgibeau-ahoussinou/alfahou](https://github.com/alfredgibeau-ahoussinou/alfahou)

## LLM open-source cloud (qualité type ChatGPT)

Le texte passe par un **modèle open-source hébergé** (Hugging Face Inference Providers, ou Groq), pas ChatGPT/Gemini propriétaires.

1. Crée un token gratuit : [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (permission *Inference Providers*)
2. En local, copie `.env.example` → `.env` et mets `ALFAHOU_LLM_API_KEY=hf_...`
3. Sur Render : ajoute la variable d’environnement `ALFAHOU_LLM_API_KEY` (ou `HF_TOKEN`)

Défaut modèle : `meta-llama/Llama-3.1-8B-Instruct` via `https://router.huggingface.co/v1`.

Sans clé : fallback conversation / skills locaux (mode léger).

## Démarrage local

```bash
cd ~/Projects/alfahou
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis colle ton token HF
uvicorn alfahou.api.app:app --reload --port 8787
```

## Capacités

| Module | Techno |
|--------|--------|
| Texte  | LLM open-source cloud (HF/Groq) + fallback |
| Image  | Diffusion DDPM + UNet (maison) |
| Vidéo  | Animation locale |
| PDF    | ReportLab |

## Licence

Projet personnel — Alfred Ahoussinou.

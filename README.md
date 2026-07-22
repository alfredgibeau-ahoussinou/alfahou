# AlfAhou

IA multimédia d’**Alfred Ahoussinou** — front React moderne + backend FastAPI + LLM cloud 2026 (GPT-OSS + recherche web).

## Stack front (pointe)

- **Vite 8** + **React 19** + **TypeScript**
- **Tailwind CSS v4**
- **Motion** (animations)
- **React Router 7** (Accueil / Manifeste / Atelier)
- Déployé sur **Netlify**

## Production

- **Site** : [https://alfahou.netlify.app](https://alfahou.netlify.app)
- **API** : [https://alfahou.onrender.com](https://alfahou.onrender.com)
- **Code** : [github.com/alfredgibeau-ahoussinou/alfahou](https://github.com/alfredgibeau-ahoussinou/alfahou)

## Dev front

```bash
cd web
npm install
npm run dev
```

## Dev API

```bash
cd ~/Projects/alfahou
source .venv/bin/activate
uvicorn alfahou.api.app:app --reload --port 8787
```

## LLM (2026)

Par défaut : **Groq `openai/gpt-oss-120b`** avec outils **browser_search** + **code_interpreter** (réponses à jour, plus Llama 3.3 déprécié).

Configurer `GROQ_API_KEY` (voir `.env.example`). Options : `groq/compound`, OpenRouter, Hugging Face.

## Licence

Projet personnel — Alfred Ahoussinou.

# AlfAhou

IA multimédia d’**Alfred Ahoussinou** — front React moderne + backend FastAPI + LLM open-source cloud.

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

## LLM

Configurer `GROQ_API_KEY` ou `HF_TOKEN` / `ALFAHOU_LLM_API_KEY` (voir `.env.example`).

## Licence

Projet personnel — Alfred Ahoussinou.

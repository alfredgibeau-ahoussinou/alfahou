# AlfAhou

IA multimédia maison d’**Alfred Ahoussinou** — texte, images, vidéos et PDF, **sans API cloud**.

Les réseaux (transformer, diffusion, encodeur) sont implémentés et entraînés localement (PyTorch + Apple Silicon MPS).

## Démarrage rapide

```bash
cd ~/Projects/alfahou
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/bootstrap.py        # entraîne les mini-modèles
uvicorn alfahou.api.app:app --reload --port 8787
```

Ouvre [http://127.0.0.1:8787](http://127.0.0.1:8787).

## Capacités

| Module | Techno from scratch |
|--------|---------------------|
| Texte  | Mini-GPT (transformer decoder) |
| Image  | Diffusion DDPM + UNet conditionné |
| Vidéo  | Séquence d’images + champ de mouvement |
| PDF    | Composition ReportLab du contenu généré |

## Architecture

```
alfahou/
  core/          device, config
  models/        text, image, video, pdf
  orchestrator/  routage multimodal
  api/           FastAPI + UI
  scripts/       bootstrap & train
```

## Licence

Projet personnel — Alfred Ahoussinou.

# CharaForge

Lernprojekt: Character-LoRA-Fine-Tuning auf [Chroma1-HD](https://huggingface.co/lodestones/Chroma1-HD)
(Apache 2.0, Flow-Matching-DiT, FLUX.1-schnell-Derivat, nativ Anime/NSFW-fähig) — Ziel ist konsistente
Charaktergenerierung über viele Bilder/Stile hinweg, langfristig sowohl Anime als auch fotorealistisch.

Phase 1: Trainings-Dummy-Charakter Frieren (Sousou no Frieren, Danbooru-Tag `frieren`), um die komplette
Pipeline (Datensammlung → Kuratierung → Captioning → Bucketing → LoRA-Training → Sampling) zu lernen und
zu bauen, bevor in Phase 2 ein eigener Charakter trainiert wird.

## Setup

```bash
pip install -e ".[dev]"
```

## Struktur

- `src/charlora/data/` — Datensammlung (Booru-API), Kuratierung, Captioning, Bucketing
- `src/charlora/model/` — Chroma1-HD laden (inkl. Quantisierung), LoRA-Layer
- `src/charlora/training/` — Flow-Matching-Trainingsloop
- `src/charlora/inference/` — Sampling/Inferenz
- `notebooks/colab_train.ipynb` — Colab-Orchestrierung
- `configs/` — charakterspezifische Configs
- `tests/` — lokale CPU-Tests (kein GPU nötig)

# MenMo5i // AI Streetwear Design Studio

**MenMo5i** is a Django 6 platform for generating, customizing, and ordering custom T-shirt designs using AI. Users enter text prompts and the system produces print-ready artwork through a multi-provider AI pipeline, composites it onto shirt templates, and supports a full storeflow with cart, checkout, and order management.

## Features

- **AI Design Generation** — 5-tier provider chain: Replicate Flux Schnell → Gemini 2.0 Flash → Hugging Face SDXL → Pollinations.ai → procedural PIL fallback
- **Prompt Engineering** — Raw user prompts are automatically enriched with theme expansions, quality tags, and style modifiers before hitting any AI model
- **Background Removal** — Designs default to transparent background; optional white background toggle
- **Content Filtering** — Blocks NSFW, violent, and prohibited content before generation
- **Shirt Composites** — Generated designs are layered onto shirt templates with configurable canvas coordinates
- **Export** — Download designs as 300 DPI print-ready PNG files (standalone or on shirt)
- **Design Variations** — Generate multiple AI variations of any design
- **Remix** — Fork and re-imagine other users' public designs
- **Community Gallery** — Browse, search, like, and follow other designers
- **Cart & Checkout** — Full shopping cart with size/color variants, shipping info, payment method selection
- **Order Management** — Order history, detail views, status tracking with email notifications

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.0, Python 3.12 |
| Database | SQLite (dev) / PostgreSQL (production) |
| Image Processing | Pillow, rembg, scikit-image |
| HTTP Client | httpx (async + sync) |
| Task Queue | Celery |
| Auth | Custom EmailOrUsername backend |
| Frontend | Tailwind CSS (CDN), Three.js (legacy 3D viewer) |

## Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/your-username/menmo5i.git
cd menmo5i
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

Copy the template and fill in at least one AI provider key:

```bash
cp .env.example .env
```

| Variable | Required | Provider |
|---|---|---|
| `GEMINI_API_KEY` | Recommended | [Google AI Studio](https://aistudio.google.com/apikey) — free tier |
| `HF_API_TOKEN` | Optional | [Hugging Face tokens](https://huggingface.co/settings/tokens) — `inference.serverless.write` permission |
| `REPLICATE_API_TOKEN` | Optional | [Replicate](https://replicate.com/account/api-tokens) — requires billing credit |

At minimum, set `GEMINI_API_KEY` for a fully free, working setup.

### 3. Run

```bash
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000 in your browser.

## Project Structure

```
MenMo5i/
├── MenMo5i/                    # Django project settings
│   ├── settings.py
│   └── urls.py                 # Root URL configuration
├── accounts/                   # User auth & profiles
├── core_store/                 # Store frontend, cart, checkout, orders
│   └── templates/core_store/   # Landing, design detail, cart, orders
├── generation_engine/          # AI design generation pipeline
│   ├── services/
│   │   ├── ai_engine.py        # Provider orchestrator with 5-tier fallback
│   │   ├── prompt_engine.py    # Keyword detection & prompt expansion
│   │   ├── gemini_inference.py # Gemini 2.0 Flash image generation
│   │   ├── hf_inference.py     # Hugging Face Inference Providers (SDXL)
│   │   ├── pollinations_inference.py  # Free no-token generation
│   │   ├── compositor.py       # Composite onto shirt templates
│   │   ├── remove_bg.py        # Background removal (rembg / PIL)
│   │   └── content_filter.py   # NSFW & prohibited content blocking
│   └── templates/
│       └── design_studio.html
├── community/                  # Gallery, likes, follows
├── billing/                    # Payment gateway placeholder
└── media/                      # Uploads & generated assets
```

## AI Provider Chain

The system tries providers in order, falling through on failure:

1. **Replicate** (Flux Schnell) — fastest, highest quality; needs billing credit
2. **Gemini 2.0 Flash** — free tier, good quality with built-in safety filters
3. **Hugging Face SDXL** — free serverless tier with proper token
4. **Pollinations.ai** — fully free, no API key required
5. **PIL procedural** — always works; generates geometric patterns locally

## Configuration

### Shirt Templates

Define shirt blanks through the Django admin (`/admin/generation_engine/shirttemplate/`):
- Upload a blank shirt image and a mask image
- Set `canvas_x`, `canvas_y`, `canvas_width`, `canvas_height` as percentages (0.0–1.0) to position the printable area

### Content Filtering

Edit `generation_engine/services/content_filter.py` to adjust blocked and flagged terms.

## License

Private / proprietary. All rights reserved.

# ⚡ MenMo5i

<div align="center">

[![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Concept%20%2F%20In%20Progress-7DCFFF?style=for-the-badge)](https://github.com/Mounib-Chandoul/MenMo5i)

</div>

> **من مخي** — *"From My Mind"*

MenMo5i is a product concept and engineering blueprint for a North African
streetwear marketplace. It brings limited physical drops together with a
community-curated, AI-assisted design pipeline: members submit mockups, the
community votes, and the winners become real products.

> **Repository status:** this repo currently holds the product specification
> and roadmap. The Django implementation described below is the planned
> architecture and is being built out — no application source is committed yet.

---

## The idea

Streetwear in North Africa has a strong visual language that rarely reaches
global storefronts. MenMo5i is designed as a digital syndicate where:

- **Drops are events** — limited runs with a story, not an endless catalogue.
- **Design is collaborative** — logged-in members upload mockups into the grid.
- **Curation is community-driven** — async upvote endpoints surface the best work.
- **The frontend is an experience** — GPU-composited parallax and scroll-scrubbed
  product stories instead of a generic product grid.

---

## Planned stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x / Python 3.12 |
| Async work | Celery + Redis (media handling, imports, scoring) |
| Database | PostgreSQL in production, SQLite for local development |
| Frontend | Tailwind CSS + hardware-accelerated vanilla JS (`translate3d`) |
| Auth | Django sessions and `django.contrib.auth` |
| Media | Local `media/` storage, later object storage |

## Planned features

### Storefront experience
- Parallax camera rig built entirely with `translate3d` to avoid layout reflow.
- A 300vh scroll-pinned section that scrubs through item specifications.
- A DOM-decoupled ambient cursor with eased tracking and `mix-blend-mode`.

### Member portal
- Guest → member layout mutations, registration, login and secure logout.
- Profile area for submissions and votes.

### AI design pipeline *(in progress)*
- Mockup upload for authenticated members.
- Async JSON upvote endpoint with per-user de-duplication.
- Curation queue that promotes top-voted designs into the drop pipeline.

---

## Proposed layout

```text
MenMo5i/
├── MenMo5i/            # settings.py, urls.py, wsgi.py, celery.py
├── core_store/         # models, forms, views, URLconf
│   ├── migrations/
│   └── templates/core_store/
│       ├── base.html   # shell: navbar, footer, cursor, grain filter
│       └── landing.html# scroll-scrubbed storefront
├── media/              # user submissions and product imagery
├── manage.py
└── requirements.txt
```

Key settings the implementation expects:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "landing"
LOGOUT_REDIRECT_URL = "landing"
```

---

## Roadmap

- [x] Brand identity and product specification
- [x] Storefront interaction design
- [ ] Django project skeleton and `core_store` app
- [ ] Product drop and AI submission models + migrations
- [ ] Authentication and member portal
- [ ] Async upvote endpoint with Celery scoring
- [ ] Payment and order flow
- [ ] Production deployment (PostgreSQL + Redis + object storage)

---

## License

[MIT](LICENSE) — © 2026 Mounib Chandoul.

# ⚡ MENMO5I // Premium North African Streetwear Syndicate

MenMo5i (من مخي — *"From My Mind"*) is an avant-garde, tech-driven SaaS marketplace and digital syndicate born out of the concrete geometries of North Africa. The platform mutates traditional streetwear retail by blending hyper-premium, exclusive physical fashion drops with a decentralized, community-driven AI design submission system. 

Built with a hardware-accelerated minimalist cyberpunk frontend and a robust asynchronous Django core engine.

---

## 🛠️ Tech Stack & System Architecture

* **Backend Matrix:** Django 5.x / Python 3.12
* **Asynchronous Task Workers:** Celery / Redis (Optimized for media handling & data-scrapes)
* **Database Shell:** PostgreSQL (Production) / SQLite3 (Local development)
* **Frontend Design Layer:** Tailwind CSS / Native Hardware-Accelerated JavaScript
* **Authentication Engine:** Django Native Sessions (`django.contrib.auth`)

---

## 🕹️ Key Features

### 1. The Core UX Layer
* **Parallax Camera Rig:** Fluid background parallax engine completely calculated using `translate3d` to bypass main-thread layout reflows and eliminate jitter.
* **Dynamic Content Pinning:** A 300vh scroll-pinned section that scrubs beautifully through item specifications, matching frame layouts dynamically with metadata.
* **Interactive Dynamic Cursor:** High-performance DOM-decoupled ambient pointer with fluid easing metrics (`mix-blend-mode: difference`).

### 2. Autonomous Authentication Portal
* Complete guest-to-member layout mutations.
* Secure token-isolated login, user onboarding registration, and secure background session termination.

### 3. AI Design Mutation Pipeline *(In Progress)*
* Logged-in citizens can upload custom streetwear mockups directly into the grid.
* Community curation engine with async JSON-based upvote endpoints.

---

## 🚀 Local Installation & Deployment

Follow these strict commands to clone, configure, and boot the local engine matrix.

### 1. Synchronize the Repository & Environment
```bash
# Clone the repository structure
git clone [https://github.com/yourusername/MenMo5i.git](https://github.com/yourusername/MenMo5i.git)
cd MenMo5i

# Spin up the isolated virtual environment
python3 -m venv .venv
source .venv/bin/activate

2. Inject System Dependencies
Bash

pip install --upgrade pip
pip install -r requirements.txt

(If you don't have a requirements.txt file yet, install the essential modules via: pip install django pillow absolute-extensions)
3. Initialize Databases & Migrate
Bash

# Generate database schema hooks
python manage.py makemigrations
python manage.py migrate

# Create the master root administrator
python manage.py createsuperuser

4. Boot up the Dev Grid
Bash

python manage.py runserver

Navigate to http://127.0.0.1:8000/ in your browser to inspect the application.
📂 Project Directory Breakdown
Plaintext

MenMo5i/
├── MenMo5i/                  # Core configuration shell
│   ├── __init__.py
│   ├── settings.py           # Global settings, static settings & authentication setups
│   ├── urls.py               # Root application URL routing registry
│   └── wsgi.py
├── core_store/               # Core storefront application directory
│   ├── migrations/
│   ├── templates/            # Core UI layout architecture
│   │   └── core_store/
│   │       ├── base.html     # Global shell (Navbar, Footer, Cursor engine, Grain filters)
│   │       └── landing.html  # Immersive scroll-scrub storefront catalog
│   ├── forms.py              # Secure user data ingestion controls
│   ├── models.py             # ProductDrop and AISubmission database structures
│   ├── urls.py               # Local app view endpoints
│   └── views.py              # Main application controllers and JSON responses
├── media/                    # Local dynamic file repository (User AI Uploads & Products)
├── manage.py
└── README.md

🌐 Environment Configurations (settings.py)

Ensure your local image rendering parameters are accurately mapped for development:
Python

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'landing'
LOGOUT_REDIRECT_URL = 'landing'

📑 License

© 2026 MENMO5I SYNDICATE. All aesthetic and technology structures preserved under digital lock.

# KamKarao

Trusted local workers in Banda, in your own mohalla. A Django website: customers find a checked
electrician, plumber, AC mechanic, bike mechanic, carpenter, beautician or painter near their
mohalla and call them directly. Hindi first, English second.

**Stack:** Django 5.2 · server-rendered templates · htmx (filters, sheets, login without page reloads) ·
hand-written CSS (no build step) · self-hosted Hind + Poppins fonts · SQLite on your laptop,
PostgreSQL on the server.

---

## 1. Run it on your Windows laptop

You need **Python 3.12** from python.org (tick *Add python.exe to PATH* during install).

1. Double-click **`setup_windows.bat`**. It creates a virtual environment, installs packages,
   builds the database, loads Banda's mohallas and services plus demo providers, and asks you to
   create an admin username and password.
2. Double-click **`run_windows.bat`**. The site opens at <http://127.0.0.1:8000>.

| Page | Address |
|---|---|
| Website (Hindi) | http://127.0.0.1:8000/hi/ |
| Website (English) | http://127.0.0.1:8000/en/ |
| Admin panel | http://127.0.0.1:8000/admin/ |
| Business dashboard | http://127.0.0.1:8000/admin/dashboard/ |

**Test the login:** tap *Call* on any worker, enter any 10-digit mobile number. In test mode no SMS
is sent: the OTP is shown in a yellow box and printed in the terminal.

**Open it on your phone** (same Wi-Fi): run `ipconfig`, note the IPv4 address (e.g. 192.168.1.5),
add it to `ALLOWED_HOSTS` in `.env`, then open `http://192.168.1.5:8000` on the phone.

Manual commands, if you prefer (PowerShell, inside this folder):

```powershell
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

Run the automated checks with `python manage.py test apps`.

---

## 2. What is real and what is demo

| Data | Status |
|---|---|
| 20 Banda mohallas with map points | Real names. Points are approximate centres from public map listings. Check each in *Admin → Mohallas → Open map* and correct if needed. |
| 7 services, sub-services, rate cards | Real structure. **Prices are my estimates** – change them in *Admin → Services*. |
| Service photos | Real, from Wikimedia Commons under CC licences. Credits page: `/hi/credits/`. |
| 23 providers, phone numbers, ratings, reviews | **Made up.** Numbers are dummies. |
| 4 shop banners | **Made up.** |

Provider pictures show coloured initials. Use **real photos of your real providers** (taken with
their permission during onboarding). Never use a stranger's face for a provider.

**Before launch, remove all demo data:**

```
python manage.py seed_demo --clear
```

This keeps mohallas and services and deletes providers, customers, leads, ratings, banners and requests.

---

## 3. How the site works

**Customer**
1. Picks a service and a mohalla (or *Use my location*, which only suggests the nearest mohalla and is not saved).
2. Sees workers nearest first, with distance, experience, starting price, rating, *Available today*.
   Filters: sub-service, available today, checked, 4.5+, woman provider. Sort: nearest / top rated / most experienced.
3. Numbers show masked (`+91 90XXX XXX01`). Tapping **Call** or **WhatsApp** asks for the customer's
   mobile + OTP **once** (stays logged in 30 days), then shows the full number. Every reveal is saved
   as a **lead**. A limit of 20 new numbers per day per customer stops scraping.
4. *Kaam batao* form for anyone who cannot choose: your team matches by hand.

**Provider (onboarded by your field person, no self-signup)**
- *Admin → Providers → Add*: name (Hindi + English), phone, photo, service, sub-services, mohalla,
  “travels to” (nearby only / all city), experience, ID type, last 4 digits, ID photo (stored in a
  private folder, never public), phone verified, consent recorded.
- Saved as **Draft** → select it → action **Approve and make live**. Approval is refused until
  consent and phone verification are ticked.
- The site's *Join as worker* form only creates a callback request (*Admin → Join requests*).

**Ratings and quality**
- The day after a lead, open *Admin → Dashboard → Ask these customers for a rating* and press
  **Send** – WhatsApp opens with a prepared Hindi message and the rating link.
- Only customers with a lead can rate, once per lead. Written reviews appear only after you tick
  *show review text* in *Admin → Ratings*.
- Under 3 ratings a worker shows **नया (New)** instead of stars.
- **3 “did not pick up” answers in a row pause the worker automatically.**
- *Report a problem* on every profile → *Admin → Complaints*. Mark *upheld* after hearing both sides;
  the strike count turns red at 3.

**Banners (local shop ads)**
- *Admin → Banners → Add*. Either upload a wide image (about 1200×400) **or** just type a
  headline, sub-line and button text – a clean coloured banner is drawn for you, so small shops need
  no designer.
- Placement: home strip, inside a service listing (after the 4th worker), or bottom of a profile.
  Optional: only for one service, only for some mohallas. Start and end dates – it hides itself after
  the end date. At most 2 per page, always labelled **विज्ञापन / Ad**.
- Views and clicks are counted per day; the banner page and the dashboard show this month's numbers
  to show the shop owner.

**Language**
- Every page exists at `/hi/...` and `/en/...`. The हिं | EN switch keeps you on the same page.
- Interface text: `locale/hi/LC_MESSAGES/django.po`. After editing, run
  `python scripts/translations.py compile` and restart. After adding new text to templates, run
  `python scripts/translations.py extract` to list strings that still need Hindi.
- Names of services, mohallas, providers and banners have separate Hindi and English fields in the admin.

---

## 4. Going live

### a) Real SMS OTP (MSG91)
1. Register on MSG91 and complete **DLT registration** (mandatory in India, takes days – start early).
2. Get an OTP template approved with the variable `##OTP##`, e.g.
   *“##OTP## is your KamKarao login OTP. Do not share it.”*
3. In `.env`: `OTP_PROVIDER=msg91`, `MSG91_AUTH_KEY=...`, `MSG91_TEMPLATE_ID=...`.

### b) Server (recommended: one small VPS in Mumbai, 2 GB RAM)
Any provider works (DigitalOcean/Lightsail/Hetzner/a local host). On the server with Docker installed:

```bash
git clone <your repo> kamkarao && cd kamkarao
cp .env.example .env          # set DEBUG=False, SECRET_KEY, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS,
                              # SITE_URL=https://kamkarao.com, DOMAIN, POSTGRES_PASSWORD, MSG91 keys
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
```

Point your domain's **A record** (kamkarao.com and www) to the server's IP. Caddy gets the HTTPS
certificate automatically. Generate a secret key with:
`python -c "import secrets; print(secrets.token_urlsafe(50))"`

**Backups:** add `deploy/backup.sh` to the server's crontab (instructions inside the file).
Copy the `backups/` folder off the server regularly.

### c) Photos on Cloudflare R2 (optional, later)
Create a public bucket (photos, banners) and a private bucket (ID photos), then fill the `S3_*`
lines in `.env`. Without them, photos stay on the server disk, which is fine at the start.

### d) Launch checklist
- [ ] `seed_demo --clear` run, real providers onboarded and approved
- [ ] Mohalla map points checked; rate card prices updated
- [ ] `DEBUG=False`, strong `SECRET_KEY`, real `ALLOWED_HOSTS`
- [ ] MSG91 live and tested with your own number
- [ ] `SUPPORT_WHATSAPP` set
- [ ] Privacy/terms text reviewed by a lawyer or CA (Aadhaar: store only last 4 digits – already enforced)
- [ ] Google Search Console: submit `https://kamkarao.com/sitemap.xml`

---

## 5. Project map

```
config/            settings (all secrets from .env), urls
apps/core/         cities, mohallas, services, rate cards; home, listing, search, area picker,
                   admin dashboard, seed commands, tests
apps/providers/    provider model (incl. private ID photo), ranking by distance, profile, reveal, join, complaint
apps/accounts/     customer phone + OTP login (console or MSG91)
apps/leads/        leads, ratings (auto-pause rule), complaints, “Kaam batao” requests
apps/ads/          banners + daily view/click stats
templates/         all pages; partials/ for cards, banners, icons
static/            css/app.css (design system), js/app.js, vendor/htmx, fonts, icons
locale/hi/         Hindi translations
deploy/            start script, Caddyfile, backup script
```

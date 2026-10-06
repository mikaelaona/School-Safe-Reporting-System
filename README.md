SLSU FindHub - Shared Lost & Found

This project uses Flask + SQLite so reports and claims are stored on the server instead of only in each user's browser.

Local setup

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py

Open http://127.0.0.1:5000

Demo admin password: admin123

For deployment, set these environment variables:

SECRET_KEY = a long random secret

ADMIN_PASSWORD = your chosen admin password

DATABASE_PATH = path where your database should live

The default SQLite database is data/findhub.db.

Important for Render

A Render service has an ephemeral filesystem unless a persistent disk is attached. A SQLite database stored on the normal filesystem can therefore be lost after restarts/redeploys. For persistent SQLite data on Render, use a persistent disk and point DATABASE_PATH to that disk path. Render documents that persistent disks are available for paid web services. For a production school system, a managed database such as Postgres is usually a better long-term choice.

Render settings

Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app

Connect your GitHub repository as a Render Web Service.

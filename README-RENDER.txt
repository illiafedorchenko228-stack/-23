Albert → Polina meme page with opt-in photo upload
=================================================

This is a Flask Web Service, not a Render Static Site.

Files to put in one GitHub repository:
  app.py
  requirements.txt
  index.html
  party-song.mp3

Render settings:
  New > Web Service
  Runtime: Python
  Build Command: pip install -r requirements.txt
  Start Command: gunicorn app:app
  Health Check Path: /health

Add environment variables in Render:
  ADMIN_USER = choose a username
  ADMIN_PASSWORD = choose a long unique password

After deploy, visit https://YOUR-SERVICE.onrender.com/admin and sign in with
those values to view voluntarily submitted photos. Do not share the /admin
password. The upload page requires photo selection, an explicit consent check,
and a click on “Send photo”; camera access is never started automatically.

Storage note: the default uploads folder is on the service filesystem. Render
may clear files on redeploy/restart unless a persistent disk is configured.
For permanent storage, configure a Render disk mounted at /var/data and set
UPLOAD_DIR=/var/data/uploads. Check Render's current disk pricing before adding
a disk.

The existing Static Site remains separate. A Web Service gets its own URL;
use that new URL for the page once deployed.

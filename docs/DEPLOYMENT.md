# Deployment

Two supported paths:
- **[Render](#deploy-on-render-recommended-easiest)** — managed, one blueprint, no server admin (recommended).
- **[Ubuntu VPS](#deployment-guide--ubuntu-server-2404)** — full self-hosted Docker Compose + Nginx.

---

## Deploy on Render (recommended, easiest)

This repo ships a `render.yaml` blueprint and a `Dockerfile.render` that runs the
whole app as **one** web service (it serves both the API and `widget.js`, so no
separate Nginx is needed) plus a **managed PostgreSQL** database.

### 1. Push the code to GitHub
Render deploys from a Git repo.

```bash
git init
git add .
git commit -m "AI Chat Widget SaaS"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

> `backend/.env` is git-ignored, so your secrets are NOT pushed — good. You'll
> set them in the Render dashboard instead.

### 2. Create the Blueprint on Render
1. Go to <https://dashboard.render.com> → **New** → **Blueprint**.
2. Connect your GitHub account and pick the repo. Render reads `render.yaml`.
3. It will provision a **Postgres** (`chat-db`) and a **web service**
   (`ai-chat-widget`). `DATABASE_URL` is wired automatically.
4. When prompted, fill the secret env vars:
   - `OPENAI_API_KEY` — your OpenAI key.
   - `ADMIN_PASSWORD` — a strong admin password.
   - `PUBLIC_BASE_URL` — leave empty for now (set it in step 4).
5. Click **Apply** and wait for the build/deploy to finish. Migrations run
   automatically on boot.

### 3. Verify
- Health:  `https://<service>.onrender.com/health`
- Admin:   `https://<service>.onrender.com/admin`  (`admin` / your password)
- Widget:  `https://<service>.onrender.com/widget.js`

### 4. Set PUBLIC_BASE_URL
Copy the service URL (e.g. `https://ai-chat-widget.onrender.com`), set it as the
`PUBLIC_BASE_URL` env var on the web service, and save (this triggers a redeploy).
Now the embed snippet shown in the admin uses your real domain.

### 5. Embed on a customer site
```html
<script src="https://<service>.onrender.com/widget.js"></script>
<script>window.ChatWidget.init({ widgetId: "THE_WIDGET_ID" });</script>
```

> **Notes on the free plan:** the free web service sleeps after inactivity (first
> request after idle is slow), and the free Postgres expires after ~90 days.
> Upgrade to paid plans for production traffic. To use a custom domain, add it
> under the service's **Settings → Custom Domains** and update `PUBLIC_BASE_URL`.

---

# Deployment Guide — Ubuntu Server 24.04

This guide deploys the AI Chat Widget SaaS on a fresh Ubuntu 24.04 VPS using
Docker Compose behind Nginx.

## 1. Provision the server

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl git ufw
```

Open the firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 2. Install Docker + Compose plugin

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # apply group without re-login
docker compose version
```

## 3. Get the code

```bash
git clone <your-repo-url> chat-saas
cd chat-saas
```

## 4. Configure environment

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Set at minimum:
- `OPENAI_API_KEY` — your OpenAI key (kept server-side, never exposed).
- `ADMIN_PASSWORD` — a strong admin password.
- Keep `DATABASE_URL` pointing at the `postgres` service.

## 5. DNS

Point `chat.example.com` (an A record) at the server's public IP. Update
`server_name` in `nginx/nginx.conf` and the snippet URLs accordingly.

## 6. Launch

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

The backend runs Alembic migrations automatically on startup.

- Admin panel:  `http://chat.example.com/admin`
- API docs:     `http://chat.example.com/docs`
- Widget:       `http://chat.example.com/widget.js`

## 7. Enable HTTPS (Let's Encrypt)

Install certbot on the host and obtain a certificate:

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d chat.example.com
```

Then in `docker-compose.yml` uncomment the `443` port and the
`/etc/letsencrypt` volume on the `nginx` service, and uncomment the HTTPS
`server` block in `nginx/nginx.conf`. Rebuild:

```bash
docker compose up -d --build nginx
```

Set up auto-renewal:

```bash
sudo crontab -e
# add:
0 3 * * * certbot renew --quiet && docker compose -f /path/to/chat-saas/docker-compose.yml restart nginx
```

## 8. Operations

```bash
# Update to a new release
git pull
docker compose up -d --build

# View logs
docker compose logs -f backend
docker compose logs -f nginx

# Backup the database
docker compose exec postgres pg_dump -U chat chatdb > backup_$(date +%F).sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U chat chatdb

# Run a new migration after model changes
docker compose exec backend alembic revision --autogenerate -m "describe change"
docker compose exec backend alembic upgrade head
```

## 9. Hardening checklist

- [ ] Strong `ADMIN_PASSWORD`; consider IP-allowlisting `/admin` in Nginx.
- [ ] HTTPS enabled and HTTP redirecting to HTTPS.
- [ ] Postgres not exposed publicly (it isn't, by default — no host port).
- [ ] Regular `pg_dump` backups stored off-box.
- [ ] `OPENAI_API_KEY` only in `backend/.env`, never in the widget/browser.
- [ ] Adjust `RATE_LIMIT_CHAT` to your traffic profile.

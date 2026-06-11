# AI Chat Widget SaaS

A simplified, production-oriented, multi-tenant SaaS platform that lets you
upload company knowledge (Markdown), index it with **OpenAI File Search /
Vector Stores**, and give each customer a single `<script>` snippet to embed an
AI chat widget that answers **only** from their knowledge base.

> Built with FastAPI + PostgreSQL + OpenAI Responses API, a dependency-free
> vanilla-JS widget, Docker Compose, and Nginx.

---

## ✨ Features

- **Knowledge ingestion** — upload `.md` files; they're uploaded to OpenAI and
  attached to a per-customer Vector Store.
- **Grounded answers** — the chatbot uses File Search and is instructed to reply
  `"I could not find that information in the knowledge base."` when the answer
  isn't present (no hallucination).
- **Multi-tenant** — unlimited customers, each with `api_key` + `vector_store_id`;
  multiple websites per customer, each with its own `widget_id`.
- **Conversation memory** — per-session history persisted in PostgreSQL and
  replayed into the model.
- **Embeddable widget** — floating button, open/close window, typing indicator,
  responsive, mobile-friendly, **RTL/Arabic + English**, no external deps.
- **Security** — rate limiting, CORS, per-widget **domain validation**, API-key
  auth for management, admin Basic-Auth, input validation, secrets via env.
  The OpenAI key never reaches the browser.
- **Admin dashboard** — create customers, upload knowledge, generate widget IDs,
  view chat logs.

---

## 🗂 Project structure

```
.
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── main.py           # app wiring, CORS, rate limiting
│   │   ├── config.py         # env-based settings
│   │   ├── database.py       # SQLAlchemy engine/session/Base
│   │   ├── models.py         # Customer, Website, KnowledgeFile, ChatMessage
│   │   ├── schemas.py        # Pydantic request/response models
│   │   ├── security.py       # admin auth, API key, domain validation
│   │   ├── limiter.py        # shared SlowAPI limiter
│   │   ├── routers/          # customers, chat, admin
│   │   ├── services/         # openai_service (vector store + Responses API)
│   │   └── templates/        # admin Jinja2 pages
│   ├── alembic/              # migrations
│   ├── Dockerfile
│   ├── entrypoint.sh         # waits for DB, migrates, starts uvicorn
│   ├── requirements.txt
│   └── .env.example
├── frontend-widget/          # vanilla JS widget (widget.js) + demo.html
├── docker/                   # widget.Dockerfile (nginx image)
├── nginx/                    # nginx.conf reverse proxy + static hosting
├── docs/                     # DEPLOYMENT.md, sample-knowledge.md
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick start (local / Docker)

```bash
cp backend/.env.example backend/.env
# edit backend/.env and set OPENAI_API_KEY + ADMIN_PASSWORD

docker compose up -d --build
```

- Admin panel: <http://localhost/admin>  (Basic auth: `admin` / your password)
- API docs:    <http://localhost/docs>
- Widget:      <http://localhost/widget.js>
- Demo page:   <http://localhost/demo.html>

### Onboard your first customer

1. Open `/admin`, create a customer (e.g. *Acme Inc.*).
2. Open the customer page → upload one or more `.md` files
   (try `docs/sample-knowledge.md`). A Vector Store is created automatically.
3. Add a website domain (e.g. `localhost` for testing) → a **widget_id** is
   generated along with the embed snippet.
4. Paste the snippet into the customer's site (or `frontend-widget/demo.html`).

---

## 🔌 API reference

All `/api/customers*` endpoints require the admin Basic-Auth header.
The `/api/chat` endpoint is public but enforces per-widget domain validation.

| Method | Path                                  | Description                          |
|--------|---------------------------------------|--------------------------------------|
| POST   | `/api/customers`                      | Create a customer                    |
| GET    | `/api/customers`                      | List customers                       |
| GET    | `/api/customers/{id}`                 | Get one customer (with websites)     |
| DELETE | `/api/customers/{id}`                 | Delete customer + its vector store   |
| POST   | `/api/customers/{id}/upload`          | Upload `.md` files → index           |
| POST   | `/api/customers/{id}/websites`        | Register domain → generate widget_id |
| POST   | `/api/chat`                           | Ask a question (used by the widget)  |

### Chat request / response

```json
// POST /api/chat
{ "widget_id": "abc123", "session_id": "session001", "message": "What services do you offer?" }
```

```json
{ "answer": "We provide Cloud CRM, Invoicing, and Analytics." }
```

If the knowledge base lacks the answer:

```json
{ "answer": "I could not find that information in the knowledge base." }
```

### Example: create a customer with curl

```bash
curl -u admin:yourpassword -X POST http://localhost/api/customers \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Acme Inc."}'
```

---

## 🧩 Widget embed

```html
<script src="https://chat.example.com/widget.js"></script>
<script>
  window.ChatWidget.init({
    widgetId: "abc123"
    // optional: apiBase, title, lang ("ar"|"en"), primary (hex color)
  });
</script>
```

The widget auto-detects RTL/Arabic from `<html lang>` or the browser, and
derives the API base from the script's origin (override with `apiBase`).

---

## 🔐 Security notes

- **OpenAI key** lives only in `backend/.env`; the browser only ever calls
  `/api/chat`.
- **Domain validation** — `/api/chat` checks the request `Origin`/`Referer`
  against the website's registered domain (subdomains allowed; `localhost`
  allowed for testing).
- **Rate limiting** via SlowAPI (`RATE_LIMIT_CHAT`, default `30/minute` per IP).
- **Admin** protected by HTTP Basic auth; **management API** also accepts the
  per-customer `X-API-Key`.
- **Input validation** through Pydantic; upload type/size checks for `.md`.

---

## 🛠 Tech stack

Python 3.12 · FastAPI · OpenAI Responses API + Vector Stores · PostgreSQL ·
SQLAlchemy 2 · Alembic · Docker / Docker Compose · Nginx · Vanilla JS.

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the full Ubuntu 24.04
production deployment, HTTPS, backups, and operations.

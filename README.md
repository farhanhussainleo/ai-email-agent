# Azure Functions Email Sender — Copilot Studio Demo

This repo is just the Function part of the AI agent building process.
For the end-to-end guide (Copilot Studio agent, HTTP action, and deployment), watch the video:

A minimal Azure Functions (Python) HTTP endpoint that sends emails via **Azure Communication Services**.
The function accepts JSON in the request body, supports **recipient lists** or a **CSV string**, and allows simple **template variables** in the subject/body.

> **Note:** This repo is intentionally minimal. You’ll scaffold your own Azure Functions project in VS Code, then drop this `function_app.py` in. No `.vscode/` or `host.json` files are included here to avoid config drift.

---

## What it does

* Exposes `POST /api/send_email` (default route)
* **Required fields:** `subject`, `body`
* **Recipients:** provide either

  * `recipients`: a string (`"a@x.com,b@y.com"`) or array (`["a@x.com","b@y.com"]`), **or**
  * `csvText`: CSV string with a header named **email**
* **Templating:** optional `vars` object; placeholders like `${name}` in subject/body are substituted
* Sends via ACS using `EmailClient.from_connection_string(...)`
* Returns a JSON summary with per-recipient `messageId` or error

---

## Prerequisites

* **Python** 3.10 or 3.11 (recommended)
* **VS Code** with Azure Functions extension (or Azure Functions Core Tools v4, optional)
* An **Azure Communication Services – Email** resource with:

  * A **connection string**
  * A **verified sender** address (domain or single address)

---

## Quick start

### 1) Scaffold a new Functions project (one-time)

In VS Code:

1. Azure (rocket) icon → **Create New Project…**
2. Language: **Python**
3. Programming model: **v2**
4. Create a function: **HTTP trigger**
5. Auth level: **Function** (recommended)
6. Finish the wizard (pick a folder, name, etc.)

> The wizard creates your project structure (including `host.json`). We intentionally keep those out of git here so your environment owns them.

### 2) Drop in the code

Replace the scaffolded function file with the `function_app.py` from this repo (root-level).

### 3) Set local settings (secrets)

Create `local.settings.json` in your project **root** (do **not** commit):

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "ACS_CONNECTION_STRING": "<your acs email connection string>",
    "ACS_SENDER_EMAIL": "<sender@yourdomain.com>"
  }
}
```

### 4) Install dependencies

```bash
python3.11 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 5) Run locally

* **VS Code:** press **F5** (Start Debugging), or
* **Core Tools:** `func start`

Default local endpoint:

```
POST http://localhost:7071/api/send_email
Content-Type: application/json
```

---

## Request examples

### A) Minimal recipients list

```json
{
  "recipients": ["alice@example.com", "bob@example.com"],
  "subject": "Hello",
  "body": "Hi there!"
}
```

### B) CSV string (must include an `email` header)

```json
{
  "csvText": "email\nalice@example.com\nbob@example.com",
  "subject": "From CSV",
  "body": "Hi from CSV!"
}
```

### C) With template variables

```json
{
  "recipients": ["alice@example.com"],
  "subject": "Hello, ${name}",
  "body": "Hi ${name}, your id is ${id}.",
  "vars": { "name": "Alice", "id": "42" }
}
```

> Placeholders use Python’s `string.Template`. Unknown placeholders are left unchanged.

---

## `curl` test

**Local**

```bash
curl -X POST http://localhost:7071/api/send_email \
  -H "Content-Type: application/json" \
  -d '{"recipients":["test@example.com"],"subject":"Hello","body":"Hi there!"}'
```

**Deployed (AuthLevel = Function)**

```bash
curl -X POST "https://<your-app>.azurewebsites.net/api/send_email" \
  -H "x-functions-key: <FUNCTION_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"recipients":["test@example.com"],"subject":"Hello","body":"Hi there!"}'
```

> If you chose **Anonymous** during scaffold, you won’t need `x-functions-key`.

---

## Response shape

**200 OK**

```json
{
  "ok": true,
  "okCount": 2,
  "errorCount": 0,
  "receivedPayload": { /* your request echoed */ },
  "results": [
    { "email": "alice@example.com", "messageId": "..." },
    { "email": "bob@example.com",   "messageId": "..." }
  ]
}
```

**Possible errors**

* `415` — `Content-Type` not `application/json`
* `400` — invalid JSON / missing `subject` or `body` / no recipients given
* `400` — CSV provided without `email` header
* `500` — missing `ACS_CONNECTION_STRING` or `ACS_SENDER_EMAIL` (server misconfig)

---

## Deploy (VS Code)

1. Right-click your project → **Deploy to Function App…**
2. Select an existing Function App (or create one).
3. In Azure Portal (or VS Code), set **Application settings**:

   * `ACS_CONNECTION_STRING`
   * `ACS_SENDER_EMAIL`
4. Test with `curl` as above (remember the `x-functions-key` if Auth = Function).

---

## Files in this repo

* `function_app.py` — the HTTP function (Python, model v2)
* `requirements.txt` — minimal deps
* `.gitignore` — keeps secrets & build artifacts out

> Not included on purpose: `.vscode/`, `host.json`, `local.settings.json`. These are created by your local scaffold and/or contain secrets.

---

## Troubleshooting

* **“Content-Type must be application/json” (415)** → Add `-H "Content-Type: application/json"` to your request.
* **“Invalid JSON body” (400)** → Ensure valid JSON (quotes, commas).
* **“Missing required fields” (400)** → Provide `subject` and `body`.
* **“Provide recipients…” (400)** → Use `recipients` (string/array) or `csvText` with `email` header.
* **“Server misconfiguration…” (500)** → Set `ACS_CONNECTION_STRING` and `ACS_SENDER_EMAIL` in local settings or Azure App Settings.
* **Send failures per recipient** → Check sender verification in ACS, connection string correctness, and allowed domains.

---

## License

MIT (feel free to adapt).

# Deployment

## Streamlit Community Cloud (free, recommended)

The app deploys straight from GitHub and redeploys on every push.

1. Sign in at [share.streamlit.io](https://share.streamlit.io) with your GitHub account and allow access to the repository.
2. Click **Create app** → **Deploy a public app from GitHub** and fill in:
   - Repository: `virgogeetu/ai-finance-assistant`
   - Branch: `main`
   - Main file path: `ui/app.py`
   - App URL: pick a name, e.g. `ai-finance-assistant`
3. Open **Advanced settings** and choose **Python 3.12**.
4. Click **Deploy**. The first build takes a few minutes while it installs `requirements.txt`; the search index is built automatically on first start.

### Modes

| Mode | Secrets to add (Advanced settings → Secrets) | What visitors get | Cost |
|---|---|---|---|
| **Demo (default)** | none | Answers built from the knowledge base and calculators; free market data from Yahoo Finance (or labelled sample data if unavailable) | Free |
| **Full AI** | `LLM_PROVIDER = "openai"`, `OPENAI_API_KEY = "…"`, optionally `ALPHA_VANTAGE_API_KEY = "…"`, `EMBEDDING_PROVIDER = "openai"` | AI-written answers, image and scan reading, voice input | Every visitor's question uses **your** API credits |

Secrets are entered in TOML format, one per line, for example `LLM_PROVIDER = "openai"`. Streamlit exposes top-level secrets as environment variables, which is how the app reads its settings. **Never commit `.env` or `.streamlit/secrets.toml`**; both are in `.gitignore`.

If you add API keys, keep costs under control: set a monthly spending limit in your OpenAI account, and consider making the app private (app **Settings** → **Sharing** → only specific viewers).

### Guardrails

The app ships with protections for public hosting (misuse filter, prompt-injection filter, personal-data redaction, usage limits, file limits, hidden error details). Limits can be tuned with secrets such as `QUESTIONS_PER_MINUTE = "5"`. See [security.md](security.md).

### Updating the site

Commit and push to `main`; Streamlit Cloud picks up the change and restarts the app within a minute or two.

### Troubleshooting

- **Build fails installing packages**: check the build log; make sure `sentence-transformers` stays commented out in `requirements.txt` (it pulls in PyTorch, which is too large for the free tier).
- **"Sample data" everywhere**: Yahoo Finance may be rate-limiting the shared server; add an `ALPHA_VANTAGE_API_KEY` secret.
- **App sleeps**: free apps sleep after a period without visitors; the first visit wakes them up in under a minute.

## Docker (any host)

```bash
docker build -t ai-finance-assistant .
docker run -p 8501:8501 --env-file .env ai-finance-assistant
```

`.dockerignore` keeps `.env` out of the image; keys are passed at run time. This works on Hugging Face Spaces (Docker SDK), Render, Railway, Fly.io or any VM.

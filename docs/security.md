# Security and guardrails

The app is designed to be hosted publicly. This page lists what could go wrong and what stops it. Every guardrail has automated tests (`tests/test_guardrails.py`, plus `test_chat_box_applies_guardrails` in `tests/test_ui.py`).

## Threats and protections

| Risk | Protection | Where |
|---|---|---|
| **Help with wrongdoing** (tax evasion, money laundering, insider trading, Ponzi or pump-and-dump schemes, fake documents, card or identity theft) | Requests to *do* these are refused with a friendly explanation before any agent or AI runs. Questions *about* them ("what is money laundering?", "is insider trading illegal?") are still answered, because they are educational. | `core/guardrails.py` `check_question`; `agents/base.py` instructions |
| **Prompt injection** ("ignore your instructions", "reveal your system prompt / API key", "developer mode") | Refused up front; the AI's instructions also say never to reveal internals and to treat files and context as information, never as instructions. Uploaded files are labelled as data in every prompt. | `check_question`; `agents/base.py` `STYLE_GUIDE` and `compose()` |
| **Personal data** (Social Security numbers, card numbers, account or routing numbers, email addresses) | Removed from questions and uploaded files **before** they are stored, shown, logged or sent to an AI provider; the visitor is told what was removed. Card numbers are checked with the Luhn checksum so ordinary large numbers are kept. | `redact_pii`; `workflow/graph.py` `chat()`; `ui/app.py` |
| **Leaked API keys** | Keys live only in environment variables or hosting secrets, never in the repo (`.env` and `.streamlit/secrets.toml` are git-ignored; `.dockerignore` keeps them out of images). Error messages are scrubbed of `apikey=…` and key-shaped strings before they can be shown or logged. Visitors see only error types, never tracebacks. | `redact_secrets`; `data/market_data.py`; `.streamlit/config.toml` `showErrorDetails = "type"` |
| **Cost abuse / flooding** | Per visitor: 8 questions a minute and 60 an hour. Whole site: 2,000 questions a day. Limits are checked **before** paid work such as reading images or transcribing audio. Question length is capped at 1,000 characters. All limits are configurable. | `UsageGuard`; `ui/app.py`; `config.py` |
| **Malicious or huge files** | Allowed types only; at most 5 files of 10 MB each per message; PDFs read up to 60 pages; images over 40 megapixels refused (decompression bombs); spreadsheets read up to 10 sheets × 5,000 rows; extracted text capped at 60,000 characters. A bad file produces a note, never a crash. | `core/attachments.py`; `.streamlit/config.toml` `maxUploadSize` |
| **Malicious links** (e.g. `javascript:` in a news feed) | Only `http`/`https` links are rendered; HTML built by the app is escaped. | `safe_url`; `ui/app.py` |
| **Cross-site request forgery** | Streamlit's XSRF protection is on. | `.streamlit/config.toml` |
| **Visitor tracking** | Streamlit usage statistics are turned off. | `.streamlit/config.toml` `gatherUsageStats = false` |

## Settings

Override any limit with an environment variable or a hosting secret:

| Variable | Default | Meaning |
|---|---|---|
| `MAX_QUESTION_CHARS` | 1000 | Longest question accepted |
| `QUESTIONS_PER_MINUTE` | 8 | Per visitor |
| `QUESTIONS_PER_HOUR` | 60 | Per visitor |
| `SITE_QUESTIONS_PER_DAY` | 2000 | All visitors together |
| `MAX_FILES_PER_MESSAGE` | 5 | Attachments per message |
| `MAX_UPLOAD_MB` | 10 | Per file |

Visitors are identified by IP address when the server can see it, otherwise by browser session; the site-wide daily cap applies either way.

## Limits of these guardrails

- The misuse filter uses patterns, not an AI judge. It is tuned to block clear requests and never block normal questions; a determined user can rephrase. The AI's own instructions are the second line of defence.
- Personal-data redaction catches common formats (U.S. SSNs, card numbers, labelled account numbers, emails), not every possible identifier. The app also tells visitors not to share such details.
- Usage limits are kept in memory, so they reset when the server restarts. With API keys configured, also set a **monthly spending limit** with your AI provider.

## Reporting a problem

Open an issue on the GitHub repository, or for anything sensitive, contact the maintainer privately rather than posting details publicly.

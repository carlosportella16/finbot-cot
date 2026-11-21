# FinBot

Financial planning chatbot built with Streamlit and Gemini (`gemini-3.1-flash-lite`). It evaluates investments based on the user's profile, net worth and goals, plus current market conditions (Selic, CDI and IPCA from the Central Bank of Brazil).

> **Disclaimer:** this is an educational project. It is not investment advice. The final decision is always the user's.

## How it works

Each question goes through a **Chain-of-Thought** pipeline of three chained calls:

1. **Plan**: stateless `generate_content` with JSON output validated by Pydantic (intent, steps, whether news is needed).
2. **Analysis**: stateless `generate_content` with BCB data and, when the plan asks for it, Google Search grounding. Computes after-tax returns and checks suitability against the profile.
3. **Synthesis**: `chat.send_message`, the only call with memory. This is the answer shown in the chat.

The plan, the analysis and the news sources are kept in a collapsed "Ver raciocínio" (show reasoning) expander below each answer. If the BCB or the news search is unavailable, the answer still comes, with a short note ("análise sem taxas atualizadas", "sem notícias recentes").

### Suitability rules

1. Without a full emergency fund (6 months of living costs), the priority is building it in a daily-liquidity asset.
2. A product riskier than the user's profile is never suggested as the main option.
3. Goals with a horizon under 2 years exclude equities as the base allocation.
4. Returns are always compared net of income tax (LCI and LCA are tax-exempt).

## Project structure

```
src/
├── app.py         # Entry point: API key check, chat session, page layout
├── ui/
│   ├── header.py  # Brand mark and wordmark
│   ├── sidebar.py # Profile, goals, BCB indicators, reset buttons, reserve badge
│   └── chat.py    # Welcome screen, history, reasoning expander, error messages
├── reasoning.py   # CoT pipeline: build_plan, analyze, synthesize, run_turn (+ retries)
├── market.py      # BCB indicators (python-bcb), cached for 1 h
├── prompts.py     # SYSTEM_INSTRUCTION and the plan, analysis and synthesis prompts
└── models.py      # Pydantic models: InvestorProfile, Goal, Plan, Source, TurnResult
.streamlit/
└── config.toml    # Light and dark theme
requirements.txt   # Pinned dependencies
.env.example       # Template for .env (GEMINI_API_KEY=)
```

## Dependencies

| Library | Role |
| --- | --- |
| `streamlit` | Chat UI |
| `google-genai` | Gemini SDK |
| `pydantic` | Plan schema and profile validation |
| `python-bcb` | Selic, CDI and IPCA from the Central Bank SGS |
| `pandas` | BCB series handling |
| `python-dotenv` | Loads `GEMINI_API_KEY` from `.env` |
| `tenacity` | Retry with exponential backoff on 429, 5xx and connection errors |
| `httpx`, `httpx2` | Connection error types of the Gemini SDK transports |
| `yfinance` | B3 quotes (optional, not used yet) |

## Running

Requires Python 3.10+ (tested with 3.12) and an API key from [Google AI Studio](https://aistudio.google.com/).

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # optional: set GEMINI_API_KEY=... (see "Gemini API key")
streamlit run src/app.py   # from the project root, so .streamlit/ and .env are found
```

### Verify setup

Checks that your key can reach the model. It should print a short greeting:

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); from google import genai; c = genai.Client(); print(c.models.generate_content(model='gemini-3.1-flash-lite', contents='olá').text)"
```

Keep the client in a variable: with `genai.Client().models.generate_content(...)` the temporary client is closed before the request is sent (`RuntimeError: Cannot send a request, as the client has been closed.`).

### Gemini API key

- **Server key:** `GEMINI_API_KEY` in `.env` (local) or in the app's Secrets (Streamlit Community Cloud). When it is set, the app uses it and never asks for a key. Everyone uses it, and you pay for every question.
- **Each user's own key:** only when the server has no key, the sidebar shows a password field for the user's key. It lives only in that browser session (not saved or logged), and the chat stays locked until a key is entered.

To make every visitor of a public deploy use their own key, simply don't set `GEMINI_API_KEY` in the deploy's Secrets.

### News search (Google Search grounding)

On the free tier, grounding for Gemini 3.x models comes with a quota of 0 and returns `429 RESOURCE_EXHAUSTED`. Enable billing on the key's project in Google AI Studio to get news and sources. Without it, the app still works and answers with the note "sem notícias recentes".

## Usage

1. If there is no `GEMINI_API_KEY` in `.env`, paste your Gemini API key in the sidebar (free at [Google AI Studio](https://aistudio.google.com/apikey)).
2. Fill in the profile in the sidebar: investor profile, invested assets, emergency fund, monthly costs, monthly contribution and goals.
3. Ask questions in the chat, e.g. "Tenho R$ 20 mil na poupança, onde aplicar?" (I have R$ 20k in savings, where should I invest it?).
4. While it answers, three loading messages show the stages: plan, analysis and synthesis.
5. Open "Ver raciocínio" below an answer to see the plan, the calculations and the sources.
6. Use "Nova conversa" (new conversation) to reset the chat and the model's memory while keeping the profile, or "Limpar perfil" (clear profile) to also reset the profile and goals.

## Error handling

| Failure | What the user sees |
| --- | --- |
| No key (server or user) | Asks for the user's key in the sidebar; chat locked until then |
| Invalid key (400/401/403) | "Chave inválida ou sem permissão", no retry |
| Rate limit (429) | Up to 3 retries (2 s, 4 s, 8 s), then "Limite atingido, aguarde um minuto" |
| Server error (5xx) | Same retries, then a "service unavailable" message |
| No connection / timeout | Same retries, then "Sem conexão com o Gemini" |
| BCB unavailable | Sidebar warning; answer with the note "análise sem taxas atualizadas" |
| News search fails or finds nothing | Answer with the note "sem notícias recentes" |
| Unexpected error | Short message on screen; traceback only in the terminal |

A failed turn is not stored: the chat history and the model's memory stay as they were.

## Manual tests

| # | Scenario | Expected |
| --- | --- | --- |
| T1 | Start without any Gemini key | Prompt to enter a key in the sidebar, chat locked, no traceback |
| T2 | Moderate profile: "Tenho R$ 20 mil na poupança, onde aplicar?" | Plan with 3–6 steps, analysis with after-tax returns vs. current CDI, answer with disclaimer |
| T3 | Then: "E se eu precisar do dinheiro em 1 ano?" | Reuses the R$ 20k and adjusts liquidity |
| T4 | "Como a última decisão do Copom afeta minha carteira?" | Plan needs news; sources listed in the expander |
| T5 | Conservative, no emergency fund: "Vale comprar ações?" | Prioritizes the emergency fund, stocks only as a warning |
| T6 | Switch to aggressive mid-conversation | History kept, tone adjusted |
| T7 | "Nova conversa", then "quanto eu tinha na poupança?" | The bot doesn't know; the profile is kept |
| T8 | BCB unavailable | Answer with the note "análise sem taxas atualizadas" |
| T9 | Repeated 429 | Retries, then a friendly message |

## Video

Presentation video: _TBD_

## Authors

Carlos Portella and Felipe Silva

## License

[MIT](LICENSE)

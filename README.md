# FinBot

Financial planning chatbot built with Streamlit and Gemini (`gemini-3.1-flash-lite`). It evaluates investments based on the user's profile, net worth and goals, plus current market conditions (Selic, CDI and IPCA from the Central Bank of Brazil).

> **Disclaimer:** this is an educational project. It is not investment advice. The final decision is always the user's.

## How it works

Each question goes through a **Chain-of-Thought** pipeline of three chained calls:

1. **Plan**: stateless `generate_content` with JSON output validated by Pydantic (intent, steps, whether news is needed).
2. **Analysis**: stateless `generate_content` with BCB data and, when the plan asks for it, Google Search grounding. Computes after-tax returns and checks suitability against the profile.
3. **Synthesis**: `chat.send_message`, the only call with memory. This is the answer shown in the chat.

The plan and analysis are kept in the "Ver raciocínio" (show reasoning) expander below each answer.

### Suitability rules

1. Without a full emergency fund (6 months of living costs), the priority is building it in a daily-liquidity asset.
2. A product riskier than the user's profile is never suggested as the main option.
3. Goals with a horizon under 2 years exclude equities as the base allocation.
4. Returns are always compared net of income tax (LCI and LCA are tax-exempt).

## Project structure

```
app.py           # Streamlit UI: sidebar, chat, reasoning expander
raciocinio.py    # CoT pipeline: gerar_plano, analisar, sintetizar, executar_turno
mercado.py       # BCB indicators (python-bcb) and optional quotes (yfinance)
prompts.py       # SYSTEM_INSTRUCTION and prompt templates
modelos.py       # Pydantic models: PerfilInvestidor, Objetivo, Plano, ResultadoTurno
openspec/        # Project specs and changes (OpenSpec)
```

## Running

Requires Python 3.10+ and an API key from [Google AI Studio](https://aistudio.google.com/).

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # set GEMINI_API_KEY=...
streamlit run app.py
```

## Usage

1. Fill in the profile in the sidebar: investor profile, invested assets, emergency fund, monthly costs, monthly contribution and goals.
2. Ask questions in the chat, e.g. "Tenho R$ 20 mil na poupança, onde aplicar?" (I have R$ 20k in savings, where should I invest it?).
3. Open "Ver raciocínio" to see the plan, the calculations and the sources.
4. Use "Nova conversa" (new conversation) to reset the context while keeping the profile, or "Limpar perfil" (clear profile) to erase everything.

## Video

Presentation video: _TBD_

## Authors

Carlos Portella and Felipe Silva

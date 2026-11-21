"""FinBot Chain-of-Thought pipeline.

Three chained calls per turn:
1. build_plan  - stateless generate_content, JSON validated by models.Plan.
2. analyze     - stateless generate_content with BCB indicators and, only when the
                 plan asks for it, Google Search grounding.
3. synthesize  - chat.send_message, the only call recorded in the chat memory.
run_turn orchestrates them and returns a TurnResult.
"""

import streamlit as st
from google import genai
from google.genai import types
from pydantic import ValidationError

from market import get_indicators
from models import InvestorProfile, Plan, Source, TurnResult, default_plan
from prompts import ANALYSIS_PROMPT, PLAN_PROMPT, SYNTHESIS_PROMPT, SYSTEM_INSTRUCTION

MODEL = "gemini-3.1-flash-lite"
HISTORY_ITEMS = 6  # last 3 turns of the chat memory feed the stateless stages

INDICATOR_NAMES = {"selic": "Selic meta", "cdi": "CDI anualizado", "ipca_12m": "IPCA 12 meses"}


def build_plan(client: genai.Client, question: str, context: str, system: str) -> Plan:
    """Stage 1: structured plan. Falls back to default_plan on an invalid answer."""
    response = client.models.generate_content(
        model=MODEL,
        contents=PLAN_PROMPT.format(context=context, question=question),
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=Plan,
        ),
    )
    try:
        return Plan.model_validate_json(response.text)
    except (ValidationError, TypeError, ValueError):
        return default_plan(question)


def analyze(
    client: genai.Client,
    question: str,
    plan: Plan,
    context: str,
    indicators: dict,
    system: str,
) -> tuple[str, list[Source], list[str]]:
    """Stage 2: step-by-step analysis. Returns (analysis, sources, warnings)."""
    prompt = ANALYSIS_PROMPT.format(
        context=context,
        question=question,
        intent=plan.intent,
        steps="\n".join(f"- {step}" for step in plan.steps),
        indicators=format_indicators(indicators),
    )
    if plan.search_queries:
        prompt += "\nBuscas sugeridas: " + "; ".join(plan.search_queries) + "\n"

    def call(tools=None):
        return client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system, temperature=0.3, tools=tools
            ),
        )

    if not plan.needs_news:
        return call().text, [], []
    try:
        response = call([types.Tool(google_search=types.GoogleSearch())])
    except Exception:
        # Search blocked or failed: the answer still comes, without news.
        return call().text, [], ["sem notícias recentes"]
    sources = grounding_sources(response)
    # The model decides whether to actually search; no sources means no news was used.
    return response.text, sources, [] if sources else ["sem notícias recentes"]


def synthesize(chat, question: str, analysis: str) -> str:
    """Stage 3: final answer. Its config (temperature 0.5) is set when the chat is created."""
    return chat.send_message(SYNTHESIS_PROMPT.format(question=question, analysis=analysis)).text


def run_turn(client: genai.Client, chat, question: str, profile: InvestorProfile) -> TurnResult:
    system = SYSTEM_INSTRUCTION.format(profile=profile.model_dump_json(indent=2))
    context = format_history(chat.get_history()[-HISTORY_ITEMS:])
    indicators = get_indicators()
    warnings = [] if indicators else ["análise sem taxas atualizadas"]

    with st.spinner("Montando o plano de análise…"):
        plan = build_plan(client, question, context, system)
    with st.spinner("Analisando perfil, mercado e notícias…"):
        analysis, sources, search_warnings = analyze(
            client, question, plan, context, indicators, system
        )
    with st.spinner("Escrevendo a recomendação…"):
        answer = synthesize(chat, question, analysis)

    return TurnResult(
        answer=answer,
        plan=plan,
        analysis=analysis,
        sources=sources,
        warnings=warnings + search_warnings,
    )


def format_history(history: list[types.Content]) -> str:
    lines = []
    for content in history:
        text = "".join(part.text or "" for part in content.parts or [])
        lines.append(f"{'Usuário' if content.role == 'user' else 'FinBot'}: {text}")
    return "\n\n".join(lines) or "(início da conversa)"


def format_indicators(indicators: dict) -> str:
    if not indicators:
        return "Indisponíveis no momento."
    return "\n".join(
        f"- {label}: {indicators[name]['value']:.2f}% (referência {indicators[name]['date']})"
        for name, label in INDICATOR_NAMES.items()
    )


def grounding_sources(response: types.GenerateContentResponse) -> list[Source]:
    metadata = response.candidates[0].grounding_metadata if response.candidates else None
    chunks = (metadata.grounding_chunks if metadata else None) or []
    return [
        Source(title=chunk.web.title or chunk.web.uri, uri=chunk.web.uri)
        for chunk in chunks
        if chunk.web and chunk.web.uri
    ]

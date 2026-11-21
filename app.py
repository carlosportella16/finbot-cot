"""FinBot Streamlit UI.

Checks GEMINI_API_KEY, collects the investor profile in the sidebar and answers
each question through the Chain-of-Thought pipeline (reasoning.run_turn). The plan,
analysis and sources of every answer stay in a collapsed "Ver raciocínio" expander.
The profile goes into the system instruction; changing it recreates the chat with
its history.
"""

import logging
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from market import get_indicators
from models import InvestorProfile, TurnResult, parse_goals
from prompts import SYSTEM_INSTRUCTION
from reasoning import CONNECTION_ERRORS, MODEL, run_turn

RISK_LABELS = {"conservative": "Conservador", "moderate": "Moderado", "aggressive": "Arrojado"}
INDICATOR_LABELS = {"selic": "Selic", "cdi": "CDI", "ipca_12m": "IPCA 12m"}
PROFILE_KEYS = [
    "risk_profile", "invested_assets", "emergency_fund", "monthly_cost",
    "monthly_contribution", "goals",
]

logger = logging.getLogger(__name__)

st.set_page_config(page_title="FinBot", page_icon="💰")

load_dotenv()
if not os.environ.get("GEMINI_API_KEY"):
    st.error(
        "GEMINI_API_KEY não encontrada. Copie o `.env.example` para `.env` "
        "e preencha `GEMINI_API_KEY=` com a chave gerada no Google AI Studio."
    )
    st.stop()


@st.cache_resource
def get_client() -> genai.Client:
    # One long-lived client per process: an unreferenced Client is closed before
    # its request is sent.
    return genai.Client()


def create_chat(profile: InvestorProfile, history=None):
    return get_client().chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION.format(
                profile=profile.model_dump_json(indent=2)
            ),
            # The chat only runs the synthesis stage. Set here, not in send_message:
            # a per-call config replaces the whole chat config, system instruction included.
            temperature=0.5,
        ),
        history=history,
    )


def br_date(iso: str) -> str:
    year, month, day = iso.split("-")
    return f"{day}/{month}/{year}"


def render_reasoning(turn: TurnResult) -> None:
    plan = turn.plan
    with st.expander("Ver raciocínio", type="compact"):
        st.markdown(f"**Intenção:** {plan.intent}")
        if plan.related_goal:
            st.markdown(f"**Objetivo relacionado:** {plan.related_goal}")
        st.markdown(f"**Buscou notícias:** {'sim' if plan.needs_news else 'não'}")
        st.markdown("**Passos do plano**\n\n" + "\n".join(
            f"{i}. {step}" for i, step in enumerate(plan.steps, 1)
        ))
        st.markdown("**Análise**")
        st.markdown(turn.analysis)
        if turn.sources:
            st.markdown("**Fontes**\n\n" + "\n".join(
                f"- [{source.title}]({source.uri})" for source in turn.sources
            ))


def render_assistant(message: dict) -> None:
    # Shared by the history loop and the new turn, so old and new answers match.
    st.markdown(message["content"])
    turn = message["turn"]
    if turn.warnings:
        st.caption("Nota: " + "; ".join(turn.warnings) + ".")
    render_reasoning(turn)


def error_message(exc: Exception) -> str:
    """User-facing text for a failed turn (retries already happened in reasoning)."""
    if isinstance(exc, errors.APIError):
        if exc.code in (400, 401, 403):
            return "Chave inválida ou sem permissão. Confira a `GEMINI_API_KEY` no `.env`."
        if exc.code == 429:
            return "Limite atingido, aguarde um minuto e tente de novo."
        if exc.code >= 500:
            return "O Gemini está indisponível no momento. Tente de novo em instantes."
    if isinstance(exc, CONNECTION_ERRORS):
        return "Sem conexão com o Gemini. Verifique sua internet e tente de novo."
    logger.exception("Unexpected error while answering")
    return "Algo deu errado ao responder. Tente de novo."


def reset_conversation() -> None:
    # The init block below recreates the chat without history, with the current profile.
    st.session_state.pop("chat", None)
    st.session_state.pop("messages", None)


def reset_profile() -> None:
    # Runs as a callback, before the widgets exist, so their keys can be cleared.
    reset_conversation()
    for key in PROFILE_KEYS:
        st.session_state.pop(key, None)


with st.sidebar:
    with st.container(horizontal=True):
        st.button("Nova conversa", icon=":material/add_comment:", on_click=reset_conversation)
        st.button("Limpar perfil", icon=":material/restart_alt:", on_click=reset_profile)
    st.header("Seu perfil")
    risk_profile = st.radio(
        "Perfil de investidor",
        list(RISK_LABELS),
        index=1,
        format_func=RISK_LABELS.get,
        key="risk_profile",
    )
    invested_assets = st.number_input(
        "Patrimônio investido (R$)", min_value=0.0, step=1000.0, key="invested_assets"
    )
    emergency_fund = st.number_input(
        "Reserva de emergência (R$)", min_value=0.0, step=1000.0, key="emergency_fund"
    )
    monthly_cost = st.number_input(
        "Custo de vida mensal (R$)", min_value=0.0, step=100.0, key="monthly_cost"
    )
    monthly_contribution = st.number_input(
        "Aporte mensal (R$)", min_value=0.0, step=100.0, key="monthly_contribution"
    )
    st.subheader("Objetivos")
    goals_table = st.data_editor(
        pd.DataFrame(
            {
                "name": pd.Series(dtype="str"),
                "target_amount": pd.Series(dtype="float"),
                "horizon_years": pd.Series(dtype="float"),
            }
        ),
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "name": st.column_config.TextColumn("Objetivo"),
            "target_amount": st.column_config.NumberColumn("Valor-alvo (R$)", min_value=0),
            "horizon_years": st.column_config.NumberColumn("Prazo (anos)", min_value=0),
        },
        key="goals",
        alt="Objetivos financeiros com valor-alvo e prazo",
    )

    st.subheader("Mercado")
    indicators = get_indicators()
    if indicators:
        with st.container(horizontal=True):
            for name, label in INDICATOR_LABELS.items():
                st.metric(label, f"{indicators[name]['value']:.2f}%".replace(".", ","))
        selic, cdi, ipca = (indicators[n]["date"] for n in INDICATOR_LABELS)
        st.caption(
            f"Fonte: Banco Central (SGS). Selic em {br_date(selic)}, "
            f"CDI em {br_date(cdi)}, IPCA de {br_date(ipca)[3:]}."
        )
    else:
        st.warning("Indicadores do BCB indisponíveis no momento.")

profile = InvestorProfile(
    risk_profile=risk_profile,
    invested_assets=invested_assets,
    emergency_fund=emergency_fund,
    monthly_cost=monthly_cost,
    monthly_contribution=monthly_contribution,
    goals=parse_goals(goals_table.to_dict("records")),
)

# The chat session holds the model's memory, so it lives per browser session.
# The system instruction is fixed at creation, so a profile change recreates the
# chat and carries the history over.
if "chat" not in st.session_state:
    st.session_state.chat = create_chat(profile)
    st.session_state.profile = profile
    st.session_state.messages = []
elif profile != st.session_state.profile:
    st.session_state.chat = create_chat(profile, st.session_state.chat.get_history())
    st.session_state.profile = profile

st.title("FinBot")
st.sidebar.caption(
    "Conteúdo educacional. Não é recomendação de investimento; a decisão é sempre sua."
)


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            render_assistant(message)
        else:
            st.markdown(message["content"])

if question := st.chat_input("Pergunte sobre seus investimentos"):
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        try:
            turn = run_turn(get_client(), st.session_state.chat, question, profile)
        except Exception as exc:
            # The question is not stored, so screen and chat memory stay as before.
            st.error(error_message(exc))
        else:
            answer = {"role": "assistant", "content": turn.answer, "turn": turn}
            render_assistant(answer)
            st.session_state.messages += [{"role": "user", "content": question}, answer]

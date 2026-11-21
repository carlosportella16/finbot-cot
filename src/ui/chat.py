"""Chat area: welcome screen, history, the new turn and its reasoning expander."""

import logging

import streamlit as st
from google import genai
from google.genai import errors

import reasoning  # module import, so tests can patch reasoning.run_turn
from models import InvestorProfile, TurnResult

USER_AVATAR = ":material/person:"
BOT_AVATAR = ":material/finance_mode:"
# Short enough to fit a 375 px screen without being cut.
SUGGESTIONS = [
    "Onde aplicar R$ 20 mil da poupança?",
    "CDB ou LCI para 2 anos?",
    "Como montar minha reserva?",
    "O que muda com o último Copom?",
]

logger = logging.getLogger(__name__)


def render_reasoning(turn: TurnResult) -> None:
    plan = turn.plan
    with st.expander("Ver raciocínio", type="compact", icon=":material/psychology:"):
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
    if isinstance(exc, reasoning.CONNECTION_ERRORS):
        return "Sem conexão com o Gemini. Verifique sua internet e tente de novo."
    logger.exception("Unexpected error while answering")
    return "Algo deu errado ao responder. Tente de novo."


def use_suggestion() -> None:
    # Callback: hand the chosen suggestion to the turn and clear the pills.
    st.session_state.pending_question = st.session_state.suggestion
    st.session_state.suggestion = None


def render_chat(client: genai.Client, profile: InvestorProfile) -> None:
    # Read first so the welcome screen is not drawn above the first turn. The input
    # stays pinned to the bottom wherever it is called.
    question = st.chat_input("Pergunte sobre seus investimentos") or st.session_state.pop(
        "pending_question", None
    )

    if not st.session_state.messages and not question:
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            st.markdown(
                "Olá! Preencha seu perfil na barra lateral e me pergunte sobre onde investir, "
                "reserva de emergência ou o cenário de juros."
            )
            st.pills("Experimente perguntar", SUGGESTIONS, key="suggestion", on_change=use_suggestion)

    for message in st.session_state.messages:
        if message["role"] == "assistant":
            with st.chat_message("assistant", avatar=BOT_AVATAR):
                render_assistant(message)
        else:
            with st.chat_message("user", avatar=USER_AVATAR):
                st.markdown(message["content"])

    if not question:
        return
    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(question)
    with st.chat_message("assistant", avatar=BOT_AVATAR):
        try:
            turn = reasoning.run_turn(client, st.session_state.chat, question, profile)
        except Exception as exc:
            # The question is not stored, so screen and chat memory stay as before.
            st.error(error_message(exc))
        else:
            answer = {"role": "assistant", "content": turn.answer, "turn": turn}
            render_assistant(answer)
            st.session_state.messages += [{"role": "user", "content": question}, answer]

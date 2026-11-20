"""FinBot Streamlit UI.

Checks GEMINI_API_KEY, collects the investor profile in the sidebar and talks to
Gemini through a chat session that keeps the conversation context. The profile
goes into the system instruction; changing it recreates the chat with its history.
"""

import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from models import InvestorProfile, parse_goals
from prompts import SYSTEM_INSTRUCTION

MODEL = "gemini-3.1-flash-lite"
RISK_LABELS = {"conservative": "Conservador", "moderate": "Moderado", "aggressive": "Arrojado"}

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
            )
        ),
        history=history,
    )


with st.sidebar:
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
        st.markdown(message["content"])

if question := st.chat_input("Pergunte sobre seus investimentos"):
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Pensando…"):
            answer = st.session_state.chat.send_message(question).text
        st.markdown(answer)
    # Appended only after the model answered, so a failed call leaves history untouched.
    st.session_state.messages += [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ]

"""FinBot Streamlit UI.

For now it only sets up the page, checks GEMINI_API_KEY and shows the educational
disclaimer. Chat, profile and the reasoning pipeline come in later stages.
"""

import os

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(page_title="FinBot", page_icon="💰")

load_dotenv()
if not os.environ.get("GEMINI_API_KEY"):
    st.error(
        "GEMINI_API_KEY não encontrada. Copie o `.env.example` para `.env` "
        "e preencha `GEMINI_API_KEY=` com a chave gerada no Google AI Studio."
    )
    st.stop()

st.title("FinBot")
st.sidebar.caption(
    "Conteúdo educacional. Não é recomendação de investimento; a decisão é sempre sua."
)

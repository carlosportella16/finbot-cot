"""FinBot Streamlit UI.

Base chat: checks GEMINI_API_KEY, shows the educational disclaimer and talks to
Gemini through a chat session that keeps the conversation context.
"""

import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from prompts import SYSTEM_INSTRUCTION

MODEL = "gemini-3.1-flash-lite"

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


# The chat session holds the model's memory, so it lives per browser session.
if "chat" not in st.session_state:
    st.session_state.chat = get_client().chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
    )
    st.session_state.messages = []

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

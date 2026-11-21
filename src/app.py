"""FinBot Streamlit entry point.

Checks GEMINI_API_KEY, draws the sidebar (ui.sidebar) and the chat (ui.chat), and
keeps the chat session that holds the model's memory. Each question goes through the
Chain-of-Thought pipeline in reasoning.py. The profile goes into the system
instruction; changing it recreates the chat with its history.
"""

import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

from models import InvestorProfile
from prompts import SYSTEM_INSTRUCTION
from reasoning import MODEL
from ui.chat import render_chat
from ui.header import render_header
from ui.sidebar import render_sidebar

st.set_page_config(page_title="FinBot", page_icon=":material/account_balance:")

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


profile = render_sidebar()

# The chat session holds the model's memory, so it lives per browser session.
# The system instruction is fixed at creation, so a profile change recreates the
# chat and carries the history over. The reset buttons drop "chat" to start over.
if "chat" not in st.session_state:
    st.session_state.chat = create_chat(profile)
    st.session_state.profile = profile
    st.session_state.messages = []
elif profile != st.session_state.profile:
    st.session_state.chat = create_chat(profile, st.session_state.chat.get_history())
    st.session_state.profile = profile

render_header()
render_chat(get_client(), profile)

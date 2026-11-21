"""FinBot Streamlit entry point.

Picks the Gemini key (the server's GEMINI_API_KEY, or, when it is missing, the user's
own key from the sidebar), draws the sidebar (ui.sidebar) and the chat (ui.chat), and keeps the
chat session that holds the model's memory. Each question goes through the
Chain-of-Thought pipeline in reasoning.py. The profile goes into the system
instruction; changing it, or the key, recreates the chat with its history.
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
# Optional: without it (e.g. no secret on Streamlit Cloud) every user must bring a key.
SERVER_KEY = os.environ.get("GEMINI_API_KEY", "").strip()


@st.cache_resource
def get_server_client() -> genai.Client:
    # One long-lived client per process: an unreferenced Client is closed before
    # its request is sent.
    return genai.Client(api_key=SERVER_KEY)


def get_client() -> genai.Client | None:
    """The server key wins; without it, the user's key lives only in this browser session."""
    if SERVER_KEY:
        return get_server_client()
    user_key = st.session_state.get("user_api_key", "").strip()
    if not user_key:
        return None
    if st.session_state.get("user_client_key") != user_key:
        st.session_state.user_client = genai.Client(api_key=user_key)
        st.session_state.user_client_key = user_key
    return st.session_state.user_client


def create_chat(client: genai.Client, profile: InvestorProfile, history=None):
    return client.chats.create(
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


profile = render_sidebar(key_required=not SERVER_KEY)
client = get_client()
render_header()

if client is None:
    st.info(
        "Informe sua chave do Gemini na barra lateral para começar. "
        "Gere uma gratuitamente no [Google AI Studio](https://aistudio.google.com/apikey).",
        icon=":material/key:",
    )
    st.stop()

# The chat session holds the model's memory, so it lives per browser session.
# The system instruction and the key are fixed at creation, so a profile or key
# change recreates the chat and carries the history over. The reset buttons drop
# "chat" to start over.
if "chat" not in st.session_state:
    st.session_state.chat = create_chat(client, profile)
    st.session_state.messages = []
elif profile != st.session_state.profile or client is not st.session_state.chat_client:
    st.session_state.chat = create_chat(client, profile, st.session_state.chat.get_history())
st.session_state.profile = profile
st.session_state.chat_client = client

render_chat(client, profile)

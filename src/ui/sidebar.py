"""Sidebar: Gemini key, conversation actions, investor profile, goals and BCB indicators."""

import pandas as pd
import streamlit as st

from market import get_indicators
from models import InvestorProfile, parse_goals
from ui.money_input import money_input

RISK_LABELS = {"conservative": "Conservador", "moderate": "Moderado", "aggressive": "Arrojado"}
INDICATOR_LABELS = {"selic": "Selic", "cdi": "CDI", "ipca_12m": "IPCA 12m"}
PROFILE_KEYS = [
    "risk_profile", "invested_assets", "emergency_fund", "monthly_cost",
    "monthly_contribution", "goals",
]


def brl(value: float) -> str:
    return "R$ " + f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def br_date(iso: str) -> str:
    year, month, day = iso.split("-")
    return f"{day}/{month}/{year}"


def reset_conversation() -> None:
    # app.py recreates the chat without history, with the current profile.
    st.session_state.pop("chat", None)
    st.session_state.pop("messages", None)


def reset_profile() -> None:
    # Runs as a callback, before the widgets exist, so their keys can be cleared.
    reset_conversation()
    for key in PROFILE_KEYS:
        st.session_state.pop(key, None)


def render_reserve_badge(emergency_fund: float, monthly_cost: float) -> None:
    if monthly_cost <= 0:
        return
    missing = 6 * monthly_cost - emergency_fund
    if missing <= 0:
        st.badge("Reserva completa", icon=":material/check_circle:", color="green")
    else:
        st.badge("Reserva incompleta", icon=":material/warning:", color="orange")
        st.caption(f"Faltam {brl(missing)} para cobrir 6 meses de custo de vida.")


def render_key_input() -> None:
    # type="password" masks it on screen; the value stays only in this session's state.
    st.text_input(
        "Chave da API do Gemini",
        type="password",
        key="user_api_key",
        live="300ms",  # commits after a pause, no Enter needed
        placeholder="Cole sua chave aqui",
        help="Usada só nesta sessão do navegador: não é salva nem registrada.",
    )
    st.caption("Gere uma gratuitamente no [Google AI Studio](https://aistudio.google.com/apikey).")


def render_indicators() -> None:
    st.subheader("Mercado", icon=":material/monitoring:")
    indicators = get_indicators()
    if not indicators:
        st.warning("Indicadores do BCB indisponíveis no momento.")
        return
    with st.container(horizontal=True):
        for name, label in INDICATOR_LABELS.items():
            st.metric(label, f"{indicators[name]['value']:.2f}%".replace(".", ","))
    selic, cdi, ipca = (indicators[n]["date"] for n in INDICATOR_LABELS)
    st.caption(
        f"Fonte: Banco Central (SGS). Selic em {br_date(selic)}, "
        f"CDI em {br_date(cdi)}, IPCA de {br_date(ipca)[3:]}."
    )


def render_sidebar(key_required: bool) -> InvestorProfile:
    """Draws the sidebar and returns the profile the user filled in.

    key_required: the server has no GEMINI_API_KEY, so the user must bring one.
    """
    with st.sidebar:
        if key_required:
            st.subheader("Sua chave do Gemini", icon=":material/key:")
            render_key_input()
        with st.container(horizontal=True):
            st.button("Nova conversa", icon=":material/add_comment:", on_click=reset_conversation)
            st.button("Limpar perfil", icon=":material/restart_alt:", on_click=reset_profile)
        st.subheader("Seu perfil", icon=":material/person:")
        risk_profile = st.segmented_control(
            "Perfil de investidor",
            list(RISK_LABELS),
            default="moderate",
            required=True,
            format_func=RISK_LABELS.get,
            key="risk_profile",
        )
        with st.container(border=True):
            invested_assets = money_input("Patrimônio investido (R$)", key="invested_assets")
            emergency_fund = money_input("Reserva de emergência (R$)", key="emergency_fund")
            monthly_cost = money_input("Custo de vida mensal (R$)", key="monthly_cost")
            monthly_contribution = money_input("Aporte mensal (R$)", key="monthly_contribution")
            render_reserve_badge(emergency_fund, monthly_cost)
        st.subheader("Objetivos", icon=":material/flag:")
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
                "target_amount": st.column_config.NumberColumn("Valor (R$)", min_value=0),
                "horizon_years": st.column_config.NumberColumn("Anos", min_value=0),
            },
            key="goals",
            alt="Objetivos financeiros com valor-alvo e prazo",
        )
        render_indicators()
        st.caption(
            "Conteúdo educacional. Não é recomendação de investimento; a decisão é sempre sua."
        )

    return InvestorProfile(
        risk_profile=risk_profile,
        invested_assets=invested_assets,
        emergency_fund=emergency_fund,
        monthly_cost=monthly_cost,
        monthly_contribution=monthly_contribution,
        goals=parse_goals(goals_table.to_dict("records")),
    )

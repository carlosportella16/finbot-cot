"""FinBot market data.

Selic, CDI and 12-month IPCA from the Central Bank of Brazil SGS (python-bcb), cached
for 1 h, plus optional B3 quotes (yfinance). Use get_indicators().
"""

import logging
from datetime import date, timedelta

import streamlit as st
from bcb import sgs

SERIES = {"selic": 432, "cdi": 4389, "ipca_12m": 13522}

# IPCA is monthly and published with a lag, so look back far enough to always
# include its last value. Ending today matters: series 432 (Selic target) is
# filled ahead with future dates for the current target.
LOOKBACK = timedelta(days=90)

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600)
def _fetch_indicators() -> dict:
    # Exceptions are not cached, so a failed fetch is retried on the next call.
    today = date.today()
    df = sgs.get(SERIES, start=today - LOOKBACK, end=today)
    indicators = {}
    for name in SERIES:
        # Each series has its own frequency; take its own last published value.
        series = df[name].dropna()
        indicators[name] = {
            "value": float(series.iloc[-1]),
            "date": series.index[-1].date().isoformat(),
        }
    return indicators


def get_indicators() -> dict:
    """{"selic"|"cdi"|"ipca_12m": {"value": float, "date": "YYYY-MM-DD"}}, or {} if BCB fails."""
    try:
        return _fetch_indicators()
    except Exception:
        logger.exception("BCB indicators unavailable")
        return {}

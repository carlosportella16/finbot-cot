"""Page header: FinBot brand mark and wordmark.

The mark is an SVG drawn with st.image (st.html's sanitizer strips <svg> and data-URI
images). The wordmark is plain HTML/CSS through st.html (no JavaScript), styled only
with its own fb-* classes, never Streamlit's private ones. Text colors inherit the
theme, so it works in light and dark mode; only the emerald accent is fixed.
"""

import streamlit as st

MARK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#047857"/>
      <stop offset="1" stop-color="#14B8A6"/>
    </linearGradient>
  </defs>
  <rect width="52" height="52" rx="14" fill="url(#g)"/>
  <path d="M12 36 L21 27 L28 32 L40 18" fill="none" stroke="#fff" stroke-width="3.5"
        stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M33 18 H40 V25" fill="none" stroke="#fff" stroke-width="3.5"
        stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="12" cy="36" r="2.6" fill="#fff"/>
</svg>"""

WORDMARK = """
<style>
  .fb-word { margin: 0; padding: 0; font-family: inherit; font-weight: 800; line-height: 1;
             font-size: clamp(2.25rem, 7vw, 3rem); letter-spacing: -0.045em; color: inherit; }
  .fb-word span { background: linear-gradient(120deg, #059669 0%, #10B981 55%, #2DD4BF 100%);
                  -webkit-background-clip: text; background-clip: text; color: transparent; }
  .fb-tag { margin-top: 0.4rem; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.14em;
            text-transform: uppercase; opacity: 0.6; }
</style>
<div>
  <h1 class="fb-word">Fin<span>Bot</span></h1>
  <div class="fb-tag">Copiloto de investimentos · IA</div>
</div>
"""


def render_header() -> None:
    with st.container(horizontal=True, vertical_alignment="center", gap="medium"):
        st.image(MARK_SVG, width=56)
        st.html(WORDMARK, width="content")
    st.caption(
        "Analisa seu perfil, seus objetivos e as taxas do Banco Central antes de responder."
    )

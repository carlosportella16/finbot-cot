# Improvements

This document lists what changed from the development spec during implementation, and why, followed by improvements that could come next. The decisions themselves are explained in [decisions.md](decisions.md).

## Changes from the spec

| Spec | Implementation | Why |
| --- | --- | --- |
| Portuguese names: `raciocinio.py`, `gerar_plano`, `PerfilInvestidor` | English names: `reasoning.py`, `build_plan`, `InvestorProfile` | English is the convention for code and documentation in the repository; interface strings and prompts stay in Portuguese for Brazilian users |
| Five modules at the project root, UI in one `app.py` | Modules in `src/`, UI split into `src/ui/` (`header.py`, `sidebar.py`, `chat.py`, `money_input.py`) | `app.py` grew with the sidebar, the chat and the header; splitting kept each file focused, and `src/` separates code from project files |
| Indicators as one dict with a single date | One value **and one date per indicator** | Selic, CDI and IPCA have different frequencies; a single date would be wrong for at least one of them |
| Profile fields with `st.number_input` | Custom money field with a fixed comma, applied without Enter | `st.number_input` kept the zeros while typing and only applied on Enter, producing wrong values |
| Risk profile with `st.radio` | `st.segmented_control` | Three short options read better as a compact control, and it wraps on narrow screens |
| `GEMINI_API_KEY` required; app stops without it | Optional server key; otherwise each user enters their own key in the sidebar | Allows a public deploy where each visitor uses their own quota, while local runs with `.env` need no extra step |
| Reset by deleting widget keys | Widget keys with a generation number | Deleting keys only cleared the server state; the browser sent the old values back on the next rerun |
| Pin versions with `pip freeze` | Pin only the direct dependencies | A full freeze mixes dozens of transitive, platform-specific packages and makes installs on other systems fragile |
| Retry on `httpx` errors | Retry on `httpx` and `httpx2` errors | The current SDK can use either transport |
| Spinners only | Spinners plus a welcome screen with clickable suggestions, a brand header and an emergency fund badge | Helps first-time users start and makes the app look like a product in the video |
| Google Search always available | Grounding treated as optional, with a note when unavailable | On the free tier, grounding for Gemini 3.x has a quota of 0 (`429 RESOURCE_EXHAUSTED`); the app must still answer |

## Not implemented from the spec

- **Optional mini-questionnaire for the risk profile.** The user picks the profile directly. A few questions (horizon, reaction to losses) would suggest a profile for those who do not know theirs.
- **B3 quotes with `yfinance`.** The library is listed as optional in `requirements.txt` but not used. It would let the analysis comment on a ticker the user mentions (e.g. `BOVA11.SA`).
- **`st.status` as a stage checklist.** Three spinners were enough; a status block would show completed stages and their duration.

## Next steps

Ordered by value for the effort.

1. **Automated tests.** The manual tests T1–T9 in the README cover the behavior, but nothing runs them automatically. `AppTest` with a mocked `run_turn` can cover the profile, resets and error messages; the pipeline can be tested with a fake client. The money field needs a browser test.
2. **Streaming the final answer.** The synthesis could stream with `st.write_stream`, so the user starts reading while the answer is written. The plan and analysis stages cannot stream usefully, since their output is consumed by the next stage.
3. **Deterministic tax math.** After-tax returns are computed by the model, guided by the tax table in the prompt. A small Python function could compute the net return of each option and pass exact numbers to the analysis, removing the main remaining source of arithmetic mistakes.
4. **Smarter history window.** The stateless stages see the last 3 turns, including long analyses. Summarizing older turns would keep long conversations cheap without losing earlier facts.
5. **Profile questionnaire and ticker quotes**, as listed above.
6. **Persisting the profile.** Saving the profile in the browser (opt-in) would avoid refilling it after a reload, without storing data on a server.

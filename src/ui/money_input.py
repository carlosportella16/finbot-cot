"""Currency input with a fixed comma: digits enter from the right (1 -> 0,01 -> 0,12).

Inline custom component (st.components.v2). No native widget masks a value as the
user types, and st.number_input only commits on Enter or blur. The value is
committed 300 ms after the last keystroke and right away on blur.
"""

import streamlit as st

HTML = """
<label for="money"></label>
<input id="money" type="text" inputmode="numeric" autocomplete="off" placeholder="0,00" />
"""

CSS = """
:host { display: block; font-family: var(--st-font); }
label {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  color: var(--st-text-color);
}
input {
  box-sizing: border-box;
  width: 100%;
  height: 2.5rem;
  padding: 0 0.75rem;
  font: inherit;
  font-size: var(--st-base-font-size);
  color: var(--st-text-color);
  background: var(--st-secondary-background-color);
  border: 1px solid var(--st-widget-border-color, var(--st-border-color));
  border-radius: var(--st-base-radius);
  outline: none;
}
input:focus { border-color: var(--st-primary-color); }
input::placeholder { color: var(--st-text-color); opacity: 0.5; }
"""

# The input element keeps its own cents and debounce timer: the default export runs
# again on every render, and module-level state would mix the four instances.
JS = """
const FORMAT = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const MAX_DIGITS = 15;
const DEBOUNCE_MS = 300;

export default function (component) {
  const { data, parentElement, setStateValue } = component;
  const label = parentElement.querySelector("label");
  const input = parentElement.querySelector("input");
  if (!label || !input) return;
  label.textContent = data.label;

  // Zero shows as empty, so the placeholder appears and there are no zeros to delete.
  const show = () => {
    input.value = input.cents ? FORMAT.format(input.cents / 100) : "";
  };
  const commit = () => {
    clearTimeout(input.timer);
    if (input.cents !== input.sent) {
      input.sent = input.cents;
      setStateValue("value", input.cents / 100);
    }
  };

  // Python -> JS only while not typing, so a rerun never fights the user's input.
  const synced = Math.round((data.value ?? 0) * 100);
  if (!input.matches(":focus") && synced !== input.cents) {
    input.cents = synced;
    input.sent = synced;
    show();
  }

  input.oninput = () => {
    const digits = input.value.replace(/\\D/g, "").replace(/^0+/, "").slice(0, MAX_DIGITS);
    input.cents = Number(digits || 0);
    show();
    input.setSelectionRange(input.value.length, input.value.length);
    clearTimeout(input.timer);
    input.timer = setTimeout(commit, DEBOUNCE_MS);
  };
  // Digits always enter at the end, so keep the caret there.
  input.onfocus = input.onclick = () => {
    input.setSelectionRange(input.value.length, input.value.length);
  };
  input.onblur = commit;
  input.onkeydown = (event) => {
    if (event.key === "Enter") commit();
  };
}
"""

_MONEY_INPUT = st.components.v2.component("finbot_money_input", html=HTML, css=CSS, js=JS)


def money_input(label: str, key: str) -> float:
    """Draws the field and returns its value in reais (>= 0)."""
    value = st.session_state.get(key, {}).get("value", 0.0)
    result = _MONEY_INPUT(
        key=key,
        data={"label": label, "value": value},
        default={"value": value},
        on_value_change=lambda: None,
    )
    return float(result.value or 0.0)

"""FinBot Chain-of-Thought pipeline.

Three chained calls per turn: plan (JSON, stateless), analysis (stateless, with BCB
data and optional search) and synthesis (chat.send_message, the only call with memory).
Planned functions: build_plan, analyze, synthesize, run_turn.
"""

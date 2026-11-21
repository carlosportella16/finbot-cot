"""FinBot Pydantic models.

InvestorProfile, Goal, Plan (stage 1 response_schema), Source and TurnResult.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class Goal(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1)
    target_amount: float = Field(ge=0)
    horizon_years: float = Field(gt=0)


class InvestorProfile(BaseModel):
    risk_profile: Literal["conservative", "moderate", "aggressive"]
    invested_assets: float = Field(ge=0)
    emergency_fund: float = Field(ge=0)
    monthly_cost: float = Field(ge=0)  # used for the 6-month emergency fund rule
    monthly_contribution: float = Field(ge=0)
    goals: list[Goal] = []


def parse_goals(rows: list[dict]) -> list[Goal]:
    """Goals from the sidebar table; rows still being typed are skipped."""
    goals = []
    for row in rows:
        try:
            goals.append(Goal(**row))
        except ValidationError:
            pass
    return goals


class Plan(BaseModel):
    """Stage 1 output (response_schema): what to analyze and whether to search news."""

    intent: str = Field(min_length=1)
    related_goal: str | None = None
    needs_news: bool
    search_queries: list[str] = Field(max_length=3)
    steps: list[str] = Field(min_length=3, max_length=6)


def default_plan(question: str) -> Plan:
    """Fallback when the model returns an invalid plan; never searches."""
    return Plan(
        intent=question,
        needs_news=False,
        search_queries=[],
        steps=[
            "Entender o objetivo, o prazo e a liquidez que a pergunta exige",
            "Comparar as opções pela rentabilidade líquida de IR frente ao CDI",
            "Checar a adequação ao perfil e às regras de reserva e prazo",
        ],
    )


class Source(BaseModel):
    title: str  # usually the site domain; the uri is a Google redirect link
    uri: str


class TurnResult(BaseModel):
    answer: str
    plan: Plan
    analysis: str
    sources: list[Source] = []  # from the search grounding metadata
    warnings: list[str] = []

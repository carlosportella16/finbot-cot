"""FinBot Pydantic models.

InvestorProfile, Goal, Plan (stage 1 response_schema) and TurnResult.
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

"""Request schemas. Unknown fields are rejected (constitution, Principle I)."""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Goal = Literal["study", "development", "design", "gaming"]
OperatingSystem = Literal["windows", "macos", "linux"]
FormFactor = Literal["ultrabook", "laptop", "gaming", "convertible"]

STRICT = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RankingRequest(BaseModel):
    model_config = STRICT

    budget_minor: Annotated[int, Field(gt=0, le=100_000_000)]
    goals: Annotated[list[Goal], Field(min_length=1)]
    weights: dict[str, float] | None = None
    preferred_brand: Annotated[str | None, Field(max_length=60)] = None
    preferred_os: OperatingSystem | None = None
    form_factor: FormFactor | None = None
    use_saved_weights: bool = False


class RegisterRequest(BaseModel):
    model_config = STRICT

    email: Annotated[str, Field(min_length=3, max_length=254)]
    password: Annotated[str, Field(min_length=12, max_length=200)]


class LoginRequest(BaseModel):
    model_config = STRICT

    email: Annotated[str, Field(min_length=3, max_length=254)]
    password: Annotated[str, Field(min_length=1, max_length=200)]


class ProfileRequest(BaseModel):
    model_config = STRICT

    goals: Annotated[list[Goal], Field(min_length=1)]
    budget_minor: Annotated[int, Field(gt=0, le=100_000_000)]
    preferred_brand: Annotated[str | None, Field(max_length=60)] = None
    preferred_os: OperatingSystem | None = None
    form_factor: FormFactor | None = None
    weights: dict[str, float]


class ProfilePatchRequest(BaseModel):
    model_config = STRICT

    goals: list[Goal] | None = None
    budget_minor: Annotated[int | None, Field(gt=0, le=100_000_000)] = None
    preferred_brand: Annotated[str | None, Field(max_length=60)] = None
    preferred_os: OperatingSystem | None = None
    form_factor: FormFactor | None = None
    weights: dict[str, float] | None = None


class ModelRequest(BaseModel):
    model_config = STRICT

    brand: Annotated[str, Field(min_length=1, max_length=60)]
    model_name: Annotated[str, Field(min_length=1, max_length=120)]
    os: OperatingSystem
    form_factor: FormFactor
    price_minor: Annotated[int, Field(gt=0)]
    cpu_score: Annotated[int, Field(gt=0)]
    ram_gb: Annotated[int, Field(ge=4, le=256)]
    weight_g: Annotated[int, Field(ge=500, le=5000)]
    battery_minutes: Annotated[int, Field(ge=60, le=2000)]
    screen_score: Annotated[float, Field(ge=0, le=10)]
    warranty_months: Annotated[int, Field(ge=0, le=60)]


class ModelPatchRequest(BaseModel):
    model_config = STRICT

    brand: Annotated[str | None, Field(min_length=1, max_length=60)] = None
    model_name: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    os: OperatingSystem | None = None
    form_factor: FormFactor | None = None
    price_minor: Annotated[int | None, Field(gt=0)] = None
    cpu_score: Annotated[int | None, Field(gt=0)] = None
    ram_gb: Annotated[int | None, Field(ge=4, le=256)] = None
    weight_g: Annotated[int | None, Field(ge=500, le=5000)] = None
    battery_minutes: Annotated[int | None, Field(ge=60, le=2000)] = None
    screen_score: Annotated[float | None, Field(ge=0, le=10)] = None
    warranty_months: Annotated[int | None, Field(ge=0, le=60)] = None


class ComparisonRequest(BaseModel):
    model_config = STRICT

    model_ids: Annotated[list[uuid.UUID], Field(min_length=2, max_length=4)]

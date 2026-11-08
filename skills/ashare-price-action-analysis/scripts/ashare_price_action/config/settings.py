from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DecisionStance = Literal["conservative", "balanced", "aggressive", "extreme_aggressive"]
NormalizationMode = Literal["strict", "lenient"]


class PromptSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    stage2_load_full_strategy_library: bool = False
    experience_max_entries: int = Field(default=0, ge=0, le=10)
    experience_max_chars_per_entry: int = Field(default=400, ge=100, le=4000)
    stage1_inject_pattern_briefs: bool = True


class ValidationSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    normalization_mode: NormalizationMode = "lenient"
    stage1_coherence_checks: bool = False
    stage2_coherence_checks: bool = False
    trace_semantic_checks: bool = False
    strict_bar_by_bar_features: bool = False
    disable_truncation_repair: bool = False
    retry_enabled: bool = True
    retry_max: int = Field(default=3, ge=0, le=5)
    retry_max_semantic: int = Field(default=1, ge=0, le=3)
    retry_stage2: bool = True

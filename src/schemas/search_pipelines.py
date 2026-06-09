"""OpenSearch search pipeline models.

Reference: https://docs.opensearch.org/latest/search-plugins/search-pipelines/score-ranker-processor/
"""

from enum import Enum
from typing import Any

from pydantic import Field, model_serializer

from src.schemas.base import RWSBaseModel

PROCESSOR_SCORE_RANKER = "score-ranker-processor"


class PipelineProcessor(RWSBaseModel):
    processor_name: str = Field(exclude=True)
    body: RWSBaseModel

    @model_serializer
    def serialize_processor(self) -> dict[str, Any]:
        return {self.processor_name: self.body.to_dict()}


class SearchPipeline(RWSBaseModel):
    """Search pipeline body for ``PUT /_search/pipeline/{id}``."""

    description: str | None = None
    phase_results_processors: list[PipelineProcessor] | None = None


class QueryWeight(RWSBaseModel):
    """Per-subquery weights for RRF combination (must sum to 1.0)."""

    weights: list[float]


class ScoreTechnique(str, Enum):
    """Supported score-ranker combination techniques."""

    RRF = "rrf"


class Combination(RWSBaseModel):
    """RRF combination settings."""

    technique: ScoreTechnique
    rank_constant: int | None = Field(default=None, ge=1)
    parameters: QueryWeight | None = None


class ScoreRankerProcessorBody(RWSBaseModel):
    """Inner body for ``score-ranker-processor``."""

    combination: Combination

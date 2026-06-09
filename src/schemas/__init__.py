"""General schemas for OpenSearch settings and responses."""

from src.schemas.base import ORSBaseModel, RWSBaseModel
from src.schemas.opensearch_responses import (
    GetMappingResponse,
    IndexListResponse,
    SearchPipelineMapResponse,
    SearchResponse,
)
from src.schemas.search_pipelines import (
    PROCESSOR_SCORE_RANKER,
    Combination,
    PipelineProcessor,
    ScoreRankerProcessorBody,
    ScoreTechnique,
    SearchPipeline,
)

__all__ = [
    "ORSBaseModel",
    "RWSBaseModel",
    "GetMappingResponse",
    "IndexListResponse",
    "SearchPipelineMapResponse",
    "SearchResponse",
    "PipelineProcessor",
    "Combination",
    "ScoreRankerProcessorBody",
    "ScoreTechnique",
    "SearchPipeline",
    "PROCESSOR_SCORE_RANKER",
]

"""Pydantic models for OpenSearch API responses.

Shapes validated against live Aiven OpenSearch responses (see migration smoke tests).
"""

from typing import Any, Literal

from pydantic import Field, RootModel

from src.schemas.base import ORSBaseModel


class IndexListResponse(ORSBaseModel):
    """``list_indices()`` — filtered index names from ``indices.get_alias()``."""

    indices: list[str]

    @classmethod
    def from_names(cls, names: list[str]) -> "IndexListResponse":
        return cls(indices=names)


class MappingField(ORSBaseModel):
    """Single field entry inside ``mappings.properties``."""

    type: str | None = None
    dimension: int | None = None
    space_type: str | None = None
    fields: dict[str, "MappingField"] | None = None


class IndexMappings(ORSBaseModel):
    properties: dict[str, MappingField]


class IndexMappingEntry(ORSBaseModel):
    mappings: IndexMappings


class GetMappingResponse(RootModel[dict[str, IndexMappingEntry]]):
    """``get_mapping(index)`` — keyed by index name."""

    @classmethod
    def from_opensearch(cls, data: dict[str, Any]) -> "GetMappingResponse":
        return cls.model_validate(data)

    def for_index(self, index_name: str) -> IndexMappingEntry:
        return self.root[index_name]


class AliasDefinition(ORSBaseModel):
    """Alias metadata (often an empty object)."""


class IndexAliases(ORSBaseModel):
    aliases: dict[str, AliasDefinition]


class GetAliasResponse(RootModel[dict[str, IndexAliases]]):
    """``indices.get_alias()`` — keyed by index name."""

    @classmethod
    def from_opensearch(cls, data: dict[str, Any]) -> "GetAliasResponse":
        return cls.model_validate(data)


class ScoreRankerCombinationResponse(ORSBaseModel):
    technique: str
    rank_constant: int | None = None
    parameters: dict[str, Any] | None = None


class ScoreRankerProcessorResponse(ORSBaseModel):
    combination: ScoreRankerCombinationResponse


class SearchPipelineDetail(ORSBaseModel):
    """Single pipeline definition returned by the search pipeline API."""

    description: str | None = None
    phase_results_processors: list[dict[str, ScoreRankerProcessorResponse]] | None = (
        None
    )
    request_processors: list[dict[str, Any]] | None = None


class SearchPipelineMapResponse(RootModel[dict[str, SearchPipelineDetail]]):
    """``search_pipeline.get()`` — keyed by pipeline id (including ``id='*'``)."""

    @classmethod
    def from_opensearch(cls, data: dict[str, Any]) -> "SearchPipelineMapResponse":
        return cls.model_validate(data)

    def get_pipeline(self, pipeline_id: str) -> SearchPipelineDetail:
        return self.root[pipeline_id]

    @property
    def pipeline_ids(self) -> list[str]:
        return list(self.root.keys())


class ShardsInfo(ORSBaseModel):
    total: int
    successful: int
    skipped: int
    failed: int


class TotalHits(ORSBaseModel):
    value: int
    relation: Literal["eq", "gte"] | str


class SearchHit(ORSBaseModel):
    index: str = Field(alias="_index")
    id: str = Field(alias="_id")
    score: float | None = Field(default=None, alias="_score")
    source: dict[str, Any] | None = Field(default=None, alias="_source")


class SearchHits(ORSBaseModel):
    total: TotalHits | int
    max_score: float | None = None
    hits: list[SearchHit]


class SearchResponse(ORSBaseModel):
    """``search()`` default response body."""

    took: int
    timed_out: bool
    shards: ShardsInfo = Field(alias="_shards")
    hits: SearchHits


MappingField.model_rebuild()

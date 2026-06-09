"""Base models for OpenSearch request/response serialization."""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict


class ORSBaseModel(BaseModel):
    """OpenSearch **response** models (parsed from API JSON)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def from_opensearch(cls, data: Any) -> Self:
        return cls.model_validate(data)


class RWSBaseModel(BaseModel):
    """Request/wire models sent **to** OpenSearch or external APIs."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True, mode="json")

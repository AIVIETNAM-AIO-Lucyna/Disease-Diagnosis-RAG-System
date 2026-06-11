"""OpenSearch sync/async clients for index management, search, and ingestion."""

from typing import Any, Dict, List

from opensearchpy import AsyncOpenSearch, OpenSearch
from opensearchpy.helpers import async_bulk
from opensearchpy.helpers import bulk as opensearch_bulk

from src.db.vector_db.base import VectorDB
from src.schemas import (
    GetMappingResponse,
    IndexListResponse,
    SearchPipelineMapResponse,
    SearchResponse,
)
from src.settings import settings

SYSTEM_INDICES = (
    ".plugins-ml-config",
    ".ql-datasources",
    ".opensearch-sap-log-types-config",
    ".kibana_2142005270_avnadmin_1",
    ".kibana_1",
    ".opendistro_security",
)


def _opensearch_hosts() -> list[dict[str, Any]]:
    """Build the host list consumed by ``opensearchpy`` clients from settings."""
    return [{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}]


def _opensearch_client_kwargs() -> dict[str, Any]:
    """Return shared connection kwargs for sync and async OpenSearch clients."""
    return {
        "hosts": _opensearch_hosts(),
        "http_auth": (settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD),
        "use_ssl": True,
        "verify_certs": False,
        "ssl_show_warn": False,
    }


def _filter_system_indices(indices: dict[str, Any]) -> List[str]:
    """Drop Aiven/Kibana/security indices from an alias map before listing."""
    return [index for index in indices if index not in SYSTEM_INDICES]


class AsyncOpenSearchClient(VectorDB):
    """Asynchronous OpenSearch client for FastAPI and other async frameworks."""

    def __init__(self) -> None:
        """Initialize an ``AsyncOpenSearch`` connection using application settings."""
        super().__init__()
        self.client = AsyncOpenSearch(**_opensearch_client_kwargs())

    async def create_index(
        self, index_name: str, index_configuration: Dict[str, Any]
    ) -> None:
        """Create an index with the given settings and mappings.

        Args:
            index_name: Physical index name (for example ``init_diseases``).
            index_configuration: OpenSearch index body (``settings`` + ``mappings``).
        """
        await self.client.indices.create(index=index_name, body=index_configuration)

    async def get_mapping(self, index_name: str) -> GetMappingResponse:
        """Return field mappings for an index, parsed into a typed response model.

        Args:
            index_name: Index or alias to inspect.

        Returns:
            Parsed mapping keyed by index name.
        """
        raw = await self.client.indices.get_mapping(index=index_name)
        return GetMappingResponse.from_opensearch(raw)

    async def list_indices(self) -> IndexListResponse:
        """List user indices, excluding known Aiven/system indices.

        Returns:
            Filtered index names derived from ``indices.get_alias()``.
        """
        aliases = await self.client.indices.get_alias()
        return IndexListResponse.from_names(_filter_system_indices(aliases))

    async def delete_index(self, index_name: str) -> None:
        """Permanently delete an index and its documents.

        Args:
            index_name: Physical index name to remove.
        """
        await self.client.indices.delete(index=index_name)

    async def create_alias(self, alias_name: str, index_name: str) -> None:
        """Point an alias at a physical index (for example ``diseases`` -> ``init_diseases``).

        Args:
            alias_name: Stable alias used by retrieval queries.
            index_name: Backing physical index.
        """
        await self.client.indices.put_alias(index=index_name, name=alias_name)

    async def delete_alias(self, alias_name: str, index_name: str) -> None:
        """Remove an alias from a physical index without deleting the index.

        Args:
            alias_name: Alias to remove.
            index_name: Physical index the alias currently references.
        """
        await self.client.indices.delete_alias(index=index_name, name=alias_name)

    async def list_search_pipelines(
        self, pipeline_id: str = "*"
    ) -> SearchPipelineMapResponse:
        """Fetch one or all search pipelines (for example hybrid RRF fusion).

        Args:
            pipeline_id: Pipeline id or ``"*"`` for all pipelines.

        Returns:
            Parsed pipeline definitions keyed by pipeline id.
        """
        raw = await self.client.search_pipeline.get(id=pipeline_id)
        return SearchPipelineMapResponse.from_opensearch(raw)

    async def create_search_pipeline(
        self, pipeline_name: str, pipeline: Dict[str, Any]
    ) -> None:
        """Create or replace a search pipeline (``PUT /_search/pipeline/{id}``).

        Args:
            pipeline_name: Pipeline id (for example ``hybrid-rrf``).
            pipeline: Search pipeline body with ``phase_results_processors``.
        """
        await self.client.search_pipeline.put(id=pipeline_name, body=pipeline)

    async def delete_search_pipeline(self, pipeline_name: str) -> None:
        """Delete a search pipeline by id.

        Args:
            pipeline_name: Pipeline id to remove.
        """
        await self.client.search_pipeline.delete(id=pipeline_name)

    async def bulk(self, actions: List[Dict[str, Any]]) -> None:
        """Execute a OpenSearch bulk request from pre-built action dicts.

        Args:
            actions: Bulk lines (for example from ``BulkIngestRequest.to_bulk_actions()``).
        """
        if not actions:
            return

        _, errors = await async_bulk(
            self.client,
            actions,
            raise_on_error=False,
        )
        if errors:
            raise RuntimeError(
                f"Bulk request failed with {len(errors)} error(s): {errors[0]}"
            )

    async def query(
        self,
        index_name: str,
        body: Any,
        *,
        search_pipeline: str | None = None,
    ) -> SearchResponse:
        """Run a search query and return a typed response.

        Args:
            index_name: Index or alias to search.
            body: OpenSearch Query DSL body (``size``, ``query``, ``_source``, etc.).
            search_pipeline: Optional pipeline id applied as the ``search_pipeline``
                query parameter (required for hybrid + RRF queries).

        Returns:
            Parsed search hits, scores, and timing metadata.
        """
        params = {"search_pipeline": search_pipeline} if search_pipeline else None
        raw = await self.client.search(index=index_name, body=body, params=params)
        return SearchResponse.from_opensearch(raw)


class OpenSearchClient(VectorDB):
    """Synchronous OpenSearch client for scripts, migrations, and notebooks."""

    def __init__(self) -> None:
        """Initialize an ``OpenSearch`` connection using application settings."""
        super().__init__()
        self.client = OpenSearch(**_opensearch_client_kwargs())

    def create_index(
        self, index_name: str, index_configuration: Dict[str, Any]
    ) -> None:
        """Create an index with the given settings and mappings.

        Args:
            index_name: Physical index name (for example ``init_diseases``).
            index_configuration: OpenSearch index body (``settings`` + ``mappings``).
        """
        self.client.indices.create(index=index_name, body=index_configuration)

    def get_mapping(self, index_name: str) -> GetMappingResponse:
        """Return field mappings for an index, parsed into a typed response model.

        Args:
            index_name: Index or alias to inspect.

        Returns:
            Parsed mapping keyed by index name.
        """
        raw = self.client.indices.get_mapping(index=index_name)
        return GetMappingResponse.from_opensearch(raw)

    def list_indices(self) -> IndexListResponse:
        """List user indices, excluding known Aiven/system indices.

        Returns:
            Filtered index names derived from ``indices.get_alias()``.
        """
        return IndexListResponse.from_names(
            _filter_system_indices(self.client.indices.get_alias())
        )

    def delete_index(self, index_name: str) -> None:
        """Permanently delete an index and its documents.

        Args:
            index_name: Physical index name to remove.
        """
        self.client.indices.delete(index=index_name)

    def create_alias(self, alias_name: str, index_name: str) -> None:
        """Point an alias at a physical index (for example ``diseases`` -> ``init_diseases``).

        Args:
            alias_name: Stable alias used by retrieval queries.
            index_name: Backing physical index.
        """
        self.client.indices.put_alias(index=index_name, name=alias_name)

    def delete_alias(self, alias_name: str, index_name: str) -> None:
        """Remove an alias from a physical index without deleting the index.

        Args:
            alias_name: Alias to remove.
            index_name: Physical index the alias currently references.
        """
        self.client.indices.delete_alias(index=index_name, name=alias_name)

    def list_search_pipelines(
        self, pipeline_id: str = "*"
    ) -> SearchPipelineMapResponse:
        """Fetch one or all search pipelines (for example hybrid RRF fusion).

        Args:
            pipeline_id: Pipeline id or ``"*"`` for all pipelines.

        Returns:
            Parsed pipeline definitions keyed by pipeline id.
        """
        raw = self.client.search_pipeline.get(id=pipeline_id)
        return SearchPipelineMapResponse.from_opensearch(raw)

    def create_search_pipeline(
        self, pipeline_name: str, pipeline: Dict[str, Any]
    ) -> None:
        """Create or replace a search pipeline (``PUT /_search/pipeline/{id}``).

        Args:
            pipeline_name: Pipeline id (for example ``hybrid-rrf``).
            pipeline: Search pipeline body with ``phase_results_processors``.
        """
        self.client.search_pipeline.put(id=pipeline_name, body=pipeline)

    def delete_search_pipeline(self, pipeline_name: str) -> None:
        """Delete a search pipeline by id.

        Args:
            pipeline_name: Pipeline id to remove.
        """
        self.client.search_pipeline.delete(id=pipeline_name)

    def bulk(self, actions: List[Dict[str, Any]]) -> None:
        """Execute a OpenSearch bulk request from pre-built action dicts.

        Args:
            actions: Bulk lines (for example from ``BulkIngestRequest.to_bulk_actions()``).
        """
        if not actions:
            return

        _, errors = opensearch_bulk(
            self.client,
            actions,
            raise_on_error=False,
        )
        if errors:
            raise RuntimeError(
                f"Bulk request failed with {len(errors)} error(s): {errors[0]}"
            )

    def query(
        self,
        index_name: str,
        body: Any,
        *,
        search_pipeline: str | None = None,
    ) -> SearchResponse:
        """Run a search query and return a typed response.

        Args:
            index_name: Index or alias to search.
            body: OpenSearch Query DSL body (``size``, ``query``, ``_source``, etc.).
            search_pipeline: Optional pipeline id applied as the ``search_pipeline``
                query parameter (required for hybrid + RRF queries).

        Returns:
            Parsed search hits, scores, and timing metadata.
        """
        params = {"search_pipeline": search_pipeline} if search_pipeline else None
        raw = self.client.search(index=index_name, body=body, params=params)
        return SearchResponse.from_opensearch(raw)


def get_opensearch_client() -> OpenSearchClient:
    """Return a process-wide singleton sync OpenSearch client."""
    if not hasattr(get_opensearch_client, "instance"):
        get_opensearch_client.instance = OpenSearchClient()
    return get_opensearch_client.instance


def get_async_opensearch_client() -> AsyncOpenSearchClient:
    """Return a process-wide singleton async OpenSearch client."""
    if not hasattr(get_async_opensearch_client, "instance"):
        get_async_opensearch_client.instance = AsyncOpenSearchClient()
    return get_async_opensearch_client.instance

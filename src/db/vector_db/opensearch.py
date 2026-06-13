"""OpenSearch sync client for index management, search, and ingestion."""

from typing import Any, Dict, List

from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError
from opensearchpy.helpers import bulk as opensearch_bulk

from src.db.vector_db.base import VectorDB
from src.schemas import (
    GetMappingResponse,
    IndexListResponse,
    SearchPipelineMapResponse,
    SearchResponse,
)
from src.settings import settings


def _opensearch_hosts() -> list[dict[str, Any]]:
    """Build the host list consumed by ``opensearchpy`` clients from settings."""
    return [{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}]


def _opensearch_client_kwargs() -> dict[str, Any]:
    """Return shared connection kwargs for the OpenSearch client."""
    return {
        "hosts": _opensearch_hosts(),
        "http_auth": (settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD),
        "use_ssl": True,
        "verify_certs": True,
        "ssl_show_warn": False,
    }


def _filter_system_indices(indices: dict[str, Any]) -> List[str]:
    """Drop Aiven/Kibana/security indices from an alias map before listing."""
    return [index for index in indices if not index.startswith(".")]


def _build_alias_swap_actions(
    alias_name: str,
    index_name: str,
    *,
    current_indices: list[str],
) -> list[dict[str, Any]]:
    """Build ``update_aliases`` actions so ``index_name`` is the sole holder of ``alias_name``.

    Emits a ``remove`` action for every index in ``current_indices`` whose name is not
    ``index_name``, and an ``add`` action when ``index_name`` does not already hold the
    alias. Physical indices are left intact — only alias bindings change.
    """
    actions: list[dict[str, Any]] = [
        {"remove": {"index": name, "alias": alias_name}}
        for name in current_indices
        if name != index_name
    ]
    if index_name not in current_indices:
        actions.append({"add": {"index": index_name, "alias": alias_name}})
    return actions


class OpenSearchClient(VectorDB):
    """Synchronous OpenSearch client for migrations, scripts, notebooks, and services.

    FastAPI routes should call service-layer methods via ``asyncio.to_thread`` (or
    ``asyncer.asyncify``) rather than adding a separate async client here.
    """

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

    def get_alias_indices(self, alias_name: str) -> list[str]:
        """List physical indices that currently expose ``alias_name``.

        Args:
            alias_name: Alias to inspect.

        Returns:
            Index names holding the alias, or an empty list when the alias does not exist.
        """
        try:
            aliases = self.client.indices.get_alias(name=alias_name)
        except NotFoundError:
            return []
        return list(aliases.keys())

    def swap_alias(self, alias_name: str, index_name: str) -> None:
        """Point ``alias_name`` at ``index_name`` and detach it from all other indices.

        Looks up every index that currently holds ``alias_name``, removes the alias from
        each one whose name is not ``index_name``, and attaches the alias to
        ``index_name`` when it is not already there. The update is a single atomic
        ``indices.update_aliases`` call, so the alias never briefly points at nothing
        during a migration.

        Physical indices are not deleted — only alias bindings change. Drop old indices
        separately with ``delete_index`` after cutover if needed.

        Args:
            alias_name: Stable alias used by retrieval queries (for example ``diseases``).
            index_name: Physical index that should become the only alias target.
        """
        actions = _build_alias_swap_actions(
            alias_name,
            index_name,
            current_indices=self.get_alias_indices(alias_name),
        )
        if actions:
            self.client.indices.update_aliases(body={"actions": actions})

    def index_exists(self, index_name: str) -> bool:
        """Return whether a physical index exists."""
        return self.client.indices.exists(index=index_name)

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
    """Return a process-wide singleton OpenSearch client."""
    if not hasattr(get_opensearch_client, "instance"):
        get_opensearch_client.instance = OpenSearchClient()
    return get_opensearch_client.instance

"""Shared pytest configuration."""

import os

# Settings are instantiated at import time; provide defaults for unit tests.
os.environ.setdefault("OPENSEARCH_HOST", "localhost")
os.environ.setdefault("OPENSEARCH_PORT", "9200")
os.environ.setdefault("OPENSEARCH_USERNAME", "test")
os.environ.setdefault("OPENSEARCH_PASSWORD", "test")

from intertext_ingest.sources.git import GitRepositorySource
from intertext_ingest.sources.http import HttpFileSource, HttpZipSource
from intertext_ingest.sources.local import LocalSource

__all__ = [
    "GitRepositorySource",
    "HttpFileSource",
    "HttpZipSource",
    "LocalSource",
]

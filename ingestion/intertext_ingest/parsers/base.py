from typing import Protocol

from intertext_ingest.normalized import AcquiredSource, NormalizedVersion


class SourceParser(Protocol):
    def parse(self, source: AcquiredSource) -> NormalizedVersion: ...

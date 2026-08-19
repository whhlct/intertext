from typing import Protocol

from intertext_ingest.normalized import AcquiredSource, ParsedSource


class SourceParser(Protocol):
    def parse(self, source: AcquiredSource) -> ParsedSource: ...

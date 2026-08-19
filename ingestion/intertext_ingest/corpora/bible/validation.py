from dataclasses import dataclass

from intertext_ingest.normalized import ResolvedVersion


@dataclass(frozen=True)
class BibleVersionValidator:
    required_canonical_keys: tuple[str, ...] = ()
    expected_testament: str | None = None

    def validate(self, version: ResolvedVersion) -> None:
        references = [
            target
            for segment in version.segments
            for target in segment.canonical_targets
        ]
        keys = [reference.key for reference in references]
        if len(keys) != len(set(keys)):
            raise ValueError(
                f"Duplicate canonical Bible references in {version.version.slug}"
            )
        missing = sorted(set(self.required_canonical_keys) - set(keys))
        if missing:
            raise ValueError(
                f"Required Bible references missing from {version.version.slug}: "
                + ", ".join(missing)
            )
        if self.expected_testament is not None:
            unexpected = [
                reference.label
                for reference in references
                if reference.components.get("testament") != self.expected_testament
            ]
            if unexpected:
                raise ValueError(
                    f"Unexpected testament coverage in {version.version.slug}: "
                    + ", ".join(unexpected[:5])
                )

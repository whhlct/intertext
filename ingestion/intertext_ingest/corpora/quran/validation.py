from dataclasses import dataclass

from intertext_ingest.normalized import ResolvedVersion


@dataclass(frozen=True)
class QuranVersionValidator:
    expected_surah_count: int = 114
    expected_ayah_count: int = 6236
    required_canonical_keys: tuple[str, ...] = (
        "quran.1.1",
        "quran.2.255",
        "quran.114.6",
    )

    def validate(self, version: ResolvedVersion) -> None:
        references = [
            target
            for segment in version.segments
            for target in segment.canonical_targets
        ]
        keys = [reference.key for reference in references]
        if len(keys) != len(set(keys)):
            raise ValueError(
                f"Duplicate canonical Quran references in {version.version.slug}"
            )
        if len(references) != self.expected_ayah_count:
            raise ValueError(
                f"Unexpected Quran ayah count in {version.version.slug}: "
                f"{len(references)} != {self.expected_ayah_count}"
            )
        surahs: dict[int, list[int]] = {}
        for reference in references:
            surah = int(reference.components["surah"])
            ayah = int(reference.components["ayah"])
            surahs.setdefault(surah, []).append(ayah)
        if set(surahs) != set(range(1, self.expected_surah_count + 1)):
            raise ValueError(
                f"Unexpected Quran surah coverage in {version.version.slug}"
            )
        for surah, ayat in surahs.items():
            if sorted(ayat) != list(range(1, len(ayat) + 1)):
                raise ValueError(
                    f"Non-contiguous Quran ayah coverage in surah {surah}"
                )
        missing = sorted(set(self.required_canonical_keys) - set(keys))
        if missing:
            raise ValueError(
                f"Required Quran references missing from {version.version.slug}: "
                + ", ".join(missing)
            )

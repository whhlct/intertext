from typing import Any


def without_empty_values(markup: dict[str, Any]) -> dict[str, Any]:
    """Remove empty optional values without interpreting format semantics."""

    return {key: value for key, value in markup.items() if value not in (None, [], {})}

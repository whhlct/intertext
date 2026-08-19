import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from app.core.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from intertext_ingest.datasets import get_dataset
from intertext_ingest.pipeline import IngestionPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="intertext-ingest")
    subcommands = parser.add_subparsers(dest="command", required=True)
    import_parser = subcommands.add_parser(
        "import", help="Acquire and import a dataset"
    )
    import_parser.add_argument("dataset", choices=("kjv", "sblgnt"))
    import_parser.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw"),
        help="Directory for preserved raw source artifacts (default: data/raw)",
    )
    import_parser.add_argument(
        "--refresh",
        action="store_true",
        help="Reacquire the current upstream source instead of using the cache",
    )
    import_parser.add_argument(
        "--database-url",
        help="Override DATABASE_URL for this import",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "import":
        raise ValueError(f"Unsupported command: {args.command}")

    database_url = args.database_url or get_settings().database_url
    engine = create_engine(database_url, pool_pre_ping=True)
    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        result = IngestionPipeline(session_factory).run(
            get_dataset(args.dataset),
            raw_root=args.raw_dir,
            refresh=args.refresh,
        )
    finally:
        engine.dispose()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import argparse
import sys
from pathlib import Path
from pprint import pprint


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.chatbot.ingestion import ingest_et_research_pack


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest the ET research pack into MongoDB."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare records without embedding or writing to MongoDB.",
    )
    parser.add_argument(
        "--bootstrap-only",
        action="store_true",
        help="Ingest only the bootstrap chunk pack and skip live URL fetching.",
    )
    parser.add_argument(
        "--live-only",
        action="store_true",
        help="Fetch and ingest only live URLs from the ET source allow-list.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit for live source fetches.",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear existing chunks for the same source_id before upserting.",
    )
    parser.add_argument(
        "--skip-registry",
        action="store_true",
        help="Skip ingesting structured product-registry summary records.",
    )
    args = parser.parse_args()

    summary = ingest_et_research_pack(
        include_live_sources=not args.bootstrap_only,
        include_bootstrap_chunks=not args.live_only,
        include_registry_records=not args.skip_registry,
        limit=args.limit,
        clear_existing_source=not args.no_clear,
        dry_run=args.dry_run,
    )
    pprint(summary)


if __name__ == "__main__":
    main()

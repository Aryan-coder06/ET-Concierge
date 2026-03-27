import argparse
import sys
from pathlib import Path
from pprint import pprint


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.chatbot.ingestion import ingest_from_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Chunk, embed, and ingest ET source documents into MongoDB."
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        default="data/source_examples",
        help="Path to a JSON/JSONL file or a directory containing source files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare chunks without embedding or writing to MongoDB.",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear existing chunks for the same source_id before upserting.",
    )
    args = parser.parse_args()

    summary = ingest_from_path(
        Path(args.input_path),
        clear_existing_source=not args.no_clear,
        dry_run=args.dry_run,
    )
    pprint(summary)


if __name__ == "__main__":
    main()

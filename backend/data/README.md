# ET Source Data

This folder is for raw ET source documents that should be chunked, embedded, and pushed into MongoDB.

Use:

```bash
cd backend
source .venv/bin/activate
python scripts/ingest_et_sources.py data/source_examples --dry-run
python scripts/ingest_et_sources.py data/source_examples
```

Supported input formats:
- `.json`
- `.jsonl`
- a directory containing multiple `.json` or `.jsonl` files

The pipeline supports two source kinds:
- `knowledge`
- `persona`

The sample file in `data/source_examples/et_sources.sample.json` shows the expected shape.

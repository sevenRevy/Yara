from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.data_processing.hotel_rag import load_hotel_rag


def main() -> None:
    rag = load_hotel_rag(rebuild=True)
    print(
        "RAG index ready: "
        f"{len(rag.chunks)} chunks, "
        f"{rag.dimensions} dimensions, "
        f"embedding_model={rag.embedding_model}, "
        f"llm_model={rag.llm_model}"
    )


if __name__ == "__main__":
    main()

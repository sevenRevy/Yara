from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.data_processing.csv_loader import get_reservation, load_services
from backend.data_processing.hotel_rag import load_hotel_rag


def main() -> None:
    rag = load_hotel_rag(rebuild=False)
    reservation = get_reservation(1001)
    if reservation is None:
        raise SystemExit("Reservation 1001 not found")

    services = load_services()
    reply = rag.answer("Que horas funciona a piscina?", reservation, services)

    print(f"Chunks: {len(rag.chunks)}")
    print(f"Dimensions: {rag.dimensions}")
    print(f"Reply: {reply}")


if __name__ == "__main__":
    main()

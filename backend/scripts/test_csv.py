from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.data_processing.csv_loader import get_reservation


def main() -> None:
    reservation = get_reservation(1001)
    if reservation is None:
        raise SystemExit('Reservation 1001 not found')

    print(f"Reservation: {reservation['reservation_id']}")
    print(f"Guest: {reservation['guest']}")
    print(f"Room: {reservation['room_id']}")
    print(f"Type: {reservation['room_type']}")
    print(f"Breakfast: {'included' if reservation['room_breakfast'] else 'not included'}")


if __name__ == '__main__':
    main()

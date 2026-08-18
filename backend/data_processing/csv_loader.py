from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = REPO_ROOT / "data" / "csv"

_TRUE_VALUES = {"1", "true", "yes", "sim", "y"}


def _source_dir(csv_dir: Path | str | None = None) -> Path:
    return Path(csv_dir) if csv_dir is not None else CSV_DIR


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV file: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _as_bool(raw_value: str) -> bool:
    return raw_value.strip().lower() in _TRUE_VALUES


def load_reservations(csv_dir: Path | str | None = None) -> list[dict[str, Any]]:
    source_dir = _source_dir(csv_dir)
    rows = _read_csv_rows(source_dir / "reservations.csv")
    reservations: list[dict[str, Any]] = []

    for row in rows:
        reservations.append(
            {
                "reservation_id": int(row["reservation_id"]),
                "guest": row["guest"].strip(),
                "room_id": int(row["room_id"]),
                "check_in": row["check_in"].strip(),
                "check_out": row["check_out"].strip(),
            }
        )

    return reservations


def load_rooms(csv_dir: Path | str | None = None) -> list[dict[str, Any]]:
    source_dir = _source_dir(csv_dir)
    rows = _read_csv_rows(source_dir / "rooms.csv")
    rooms: list[dict[str, Any]] = []

    for row in rows:
        rooms.append(
            {
                "room_id": int(row["room_id"]),
                "type": row["type"].strip(),
                "floor": int(row["floor"]),
                "minibar": _as_bool(row["minibar"]),
                "breakfast": _as_bool(row["breakfast"]),
                "capacity": int(row["capacity"]),
            }
        )

    return rooms


def load_services(csv_dir: Path | str | None = None) -> list[dict[str, Any]]:
    source_dir = _source_dir(csv_dir)
    rows = _read_csv_rows(source_dir / "services.csv")
    services: list[dict[str, Any]] = []

    for row in rows:
        services.append(
            {
                "service_id": int(row["service_id"]),
                "name": row["name"].strip(),
                "description": row["description"].strip(),
                "included": _as_bool(row["included"]),
            }
        )

    return services


def get_reservation(
    reservation_id: int,
    csv_dir: Path | str | None = None,
) -> dict[str, Any] | None:
    source_dir = _source_dir(csv_dir)
    reservations = load_reservations(source_dir)
    rooms_by_id = {room["room_id"]: room for room in load_rooms(source_dir)}

    for reservation in reservations:
        if reservation["reservation_id"] != int(reservation_id):
            continue

        room = rooms_by_id.get(reservation["room_id"])
        if room is None:
            raise ValueError(f"Room {reservation['room_id']} not found for reservation {reservation_id}")

        bundle = {
            **reservation,
            "room_type": room["type"],
            "room_floor": room["floor"],
            "room_minibar": room["minibar"],
            "room_breakfast": room["breakfast"],
            "room_capacity": room["capacity"],
        }
        bundle["breakfast_included"] = bundle["room_breakfast"]
        return bundle

    return None


load_reservation_bundle = get_reservation

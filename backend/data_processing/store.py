from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = REPO_ROOT / "data" / "csv"
DB_PATH = REPO_ROOT / "data" / "processed" / "yara.db"

TABLES: dict[str, dict[str, Any]] = {
    "rooms": {
        "csv": "rooms.csv",
        "schema": """
            CREATE TABLE IF NOT EXISTS rooms (
                room_id INTEGER PRIMARY KEY,
                type TEXT NOT NULL,
                floor INTEGER NOT NULL,
                minibar INTEGER NOT NULL,
                breakfast INTEGER NOT NULL,
                capacity INTEGER NOT NULL
            )
        """,
        "columns": ("room_id", "type", "floor", "minibar", "breakfast", "capacity"),
        "booleans": {"minibar", "breakfast"},
        "integers": {"room_id", "floor", "capacity"},
    },
    "reservations": {
        "csv": "reservations.csv",
        "schema": """
            CREATE TABLE IF NOT EXISTS reservations (
                reservation_id INTEGER PRIMARY KEY,
                guest TEXT NOT NULL,
                room_id INTEGER NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms (room_id)
            )
        """,
        "columns": ("reservation_id", "guest", "room_id", "check_in", "check_out"),
        "booleans": set(),
        "integers": {"reservation_id", "room_id"},
    },
    "services": {
        "csv": "services.csv",
        "schema": """
            CREATE TABLE IF NOT EXISTS services (
                service_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                included INTEGER NOT NULL
            )
        """,
        "columns": ("service_id", "name", "description", "included"),
        "booleans": {"included"},
        "integers": {"service_id"},
    },
}

BOOTSTRAP_ORDER = ("rooms", "services", "reservations")
DELETE_ORDER = ("reservations", "services", "rooms")


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path is not None else DB_PATH
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def bootstrap_database(
    db_path: Path | str | None = None,
    csv_dir: Path | str | None = None,
) -> Path:
    path = Path(db_path) if db_path is not None else DB_PATH
    source_dir = Path(csv_dir) if csv_dir is not None else CSV_DIR

    path.parent.mkdir(parents=True, exist_ok=True)

    with connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for table_name in DELETE_ORDER:
            connection.execute(f"DELETE FROM {table_name}")

        for table_name in BOOTSTRAP_ORDER:
            table_spec = TABLES[table_name]
            connection.execute(table_spec["schema"])
            _import_csv(connection, source_dir / table_spec["csv"], table_name, table_spec)
        connection.commit()

    return path


def load_reservation_bundle(
    connection: sqlite3.Connection,
    reservation_id: int,
) -> dict[str, Any] | None:
    row = connection.execute(
        """
        SELECT
            r.reservation_id,
            r.guest,
            r.room_id,
            r.check_in,
            r.check_out,
            ro.type AS room_type,
            ro.floor AS room_floor,
            ro.minibar AS room_minibar,
            ro.breakfast AS room_breakfast,
            ro.capacity AS room_capacity
        FROM reservations r
        INNER JOIN rooms ro ON ro.room_id = r.room_id
        WHERE r.reservation_id = ?
        """,
        (reservation_id,),
    ).fetchone()

    return dict(row) if row is not None else None


def load_services(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT service_id, name, description, included
        FROM services
        ORDER BY service_id
        """
    ).fetchall()
    return [dict(row) for row in rows]


def format_reservation_summary(bundle: dict[str, Any]) -> str:
    breakfast = "incluido" if bundle["room_breakfast"] else "nao incluido"
    minibar = "sim" if bundle["room_minibar"] else "nao"
    return "\n".join(
        [
            f"Hospede: {bundle['guest']}",
            f"Quarto: {bundle['room_id']} ({bundle['room_type']})",
            f"Andar: {bundle['room_floor']}",
            f"Check-in: {bundle['check_in']}",
            f"Check-out: {bundle['check_out']}",
            f"Cafe da manha: {breakfast}",
            f"Frigobar: {minibar}",
            f"Capacidade: {bundle['room_capacity']} hospedes",
        ]
    )


def _import_csv(
    connection: sqlite3.Connection,
    csv_path: Path,
    table_name: str,
    table_spec: dict[str, Any],
) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV file: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    columns = list(table_spec["columns"])
    placeholders = ", ".join(["?"] * len(columns))
    column_list = ", ".join(columns)
    insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"

    for row in rows:
        values = [_coerce_value(table_spec, column, row[column]) for column in columns]
        connection.execute(insert_sql, values)


def _coerce_value(table_spec: dict[str, Any], column: str, raw_value: str) -> Any:
    value = raw_value.strip()

    if column in table_spec["booleans"]:
        return 1 if value.lower() in {"1", "true", "yes", "sim"} else 0

    if column in table_spec["integers"]:
        return int(value)

    return value

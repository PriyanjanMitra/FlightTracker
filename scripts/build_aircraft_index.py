#!/usr/bin/env python3
"""Build a compact SQLite index from the OpenSky aircraft database CSV.

Usage:
    python scripts/build_aircraft_index.py <aircraft.csv> [output.db]
"""
import csv
import pathlib
import sqlite3
import sys


def build(csv_path: pathlib.Path, out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    conn = sqlite3.connect(out_path)
    conn.execute(
        "CREATE TABLE aircraft ("
        "  icao24 TEXT PRIMARY KEY,"
        "  typecode TEXT,"
        "  manufacturer TEXT,"
        "  model TEXT,"
        "  registration TEXT,"
        "  operator TEXT,"
        "  operator_icao TEXT,"
        "  operator_iata TEXT"
        ")"
    )
    rows = 0
    skipped = 0
    with open(csv_path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f, quotechar="'")
        required = {
            "icao24", "typecode", "manufacturerName", "model", "registration",
            "operator", "operatorIcao", "operatorIata",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"Unexpected columns; missing: {sorted(missing)}")
        key = lambda r: (  # noqa: E731
            r.get("icao24", "").strip().strip("'\""),
            r.get("typecode", "").strip(),
            r.get("manufacturerName", "").strip(),
            r.get("model", "").strip(),
            r.get("registration", "").strip(),
            r.get("operator", "").strip(),
            r.get("operatorIcao", "").strip(),
            r.get("operatorIata", "").strip(),
        )
        batch: list[tuple[str, str, str, str, str, str, str, str]] = []
        for rec in reader:
            fields = key(rec)
            icao24, typecode, manufacturer, model = fields[:4]
            registration, operator, op_icao, op_iata = fields[4:]
            if not icao24:
                skipped += 1
                continue
            batch.append(
                (icao24, typecode, manufacturer, model, registration,
                 operator, op_icao, op_iata)
            )
            rows += 1
            if rows % 100000 == 0:
                conn.executemany(
                    "INSERT OR REPLACE INTO aircraft VALUES (?,?,?,?,?,?,?,?)", batch
                )
                batch.clear()
                print(f"  {rows:,} rows...")
        if batch:
            conn.executemany("INSERT OR REPLACE INTO aircraft VALUES (?,?,?,?,?,?,?,?)", batch)
    conn.commit()
    conn.execute("CREATE INDEX idx_aircraft_typecode ON aircraft(typecode)")
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM aircraft").fetchone()[0]
    conn.close()
    print(f"Done: {total:,} aircraft written to {out_path} ({skipped:,} skipped)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    csv_file = pathlib.Path(sys.argv[1])
    out_file = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path(
        "data/aircraft_registry.db"
    )
    build(csv_file, out_file)

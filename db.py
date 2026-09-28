
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "parking.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ParkingSlots (
            slot_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL CHECK (status IN ('free', 'occupied'))
        );

        CREATE TABLE IF NOT EXISTS Vehicles (
            vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            slot_id INTEGER NOT NULL,
            FOREIGN KEY (slot_id) REFERENCES ParkingSlots(slot_id)
        );

        CREATE TABLE IF NOT EXISTS Transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            plate_number TEXT NOT NULL,
            slot_id INTEGER,
            exit_time TEXT NOT NULL,
            amount_paid REAL NOT NULL,
            payment_method TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Rates (
            rate_id INTEGER PRIMARY KEY AUTOINCREMENT,
            max_hours REAL NOT NULL,
            fee REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Staff (
            staff_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Overrides (
            override_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER,
            plate_number TEXT,
            staff_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (staff_id) REFERENCES Staff(staff_id)
        );
        """
    )

    slot_count = conn.execute("SELECT COUNT(*) FROM ParkingSlots").fetchone()[0]
    if slot_count == 0:
        for slot_id in range(1, 13):
            conn.execute(
                "INSERT INTO ParkingSlots (slot_id, status) VALUES (?, 'free')",
                (slot_id,),
            )

    rate_count = conn.execute("SELECT COUNT(*) FROM Rates").fetchone()[0]
    if rate_count == 0:
        conn.executemany(
            "INSERT INTO Rates (max_hours, fee) VALUES (?, ?)",
            [
                (0.5, 0),
                (2, 50),
                (4, 100),
                (6, 300),
                (10, 500),
            ],
        )

    staff_count = conn.execute("SELECT COUNT(*) FROM Staff").fetchone()[0]
    if staff_count == 0:
        conn.executemany(
            "INSERT INTO Staff (name, role) VALUES (?, ?)",
            [
                ("Kellen Faith", "attendant"),
                ("Izary Nelson", "supervisor"),
                ("Norah Mutheu", "manager"),
            ],
        )

    conn.commit()
    conn.close()

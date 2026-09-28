import csv
import io
import sqlite3
from collections import deque
from datetime import datetime, timedelta

from flask import (
    Flask,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from db import get_connection, init_db

app = Flask(__name__)
app.secret_key = "dsa-task1-student-parking"
init_db()


waiting_queue = deque()


def now():
    return datetime.now().replace(microsecond=0)


def parse_time(value):
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def format_time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S")



def get_slots_list(conn):
    """Array/List of parking bays, in slot_id order."""
    rows = conn.execute(
        "SELECT slot_id, status FROM ParkingSlots ORDER BY slot_id"
    ).fetchall()
    return [dict(row) for row in rows]


def get_vehicles_map(conn):
    """Hash map / dictionary: plate_number -> parked vehicle."""
    rows = conn.execute(
        """
        SELECT vehicle_id, plate_number, entry_time, slot_id
        FROM Vehicles
        """
    ).fetchall()
    vehicles = {}
    for row in rows:
        vehicles[row["plate_number"]] = dict(row)
    return vehicles


def find_first_free_slot(slots):
    for slot in slots:
        if slot["status"] == "free":
            return slot["slot_id"]
    return None


def lookup_fee_from_rates(conn, duration_hours):
    
    rates = conn.execute(
        "SELECT max_hours, fee FROM Rates ORDER BY max_hours"
    ).fetchall()
    for rate in rates:
        if duration_hours <= rate["max_hours"]:
            return float(rate["fee"])
    return float(rates[-1]["fee"]) if rates else 0.0



def exception_case_1_lot_full(plate):
    """No free slots: deny entry, then add the car to the waiting queue."""
    waiting_queue.append(plate)
    flash(
        "SORRY! PARKING LOT FULL, NO SPACES AVAILABLE. ENTRY DENIED. "
        f"{plate} was added to the waiting queue.",
        "error",
    )


def exception_case_2_find_by_slot(vehicles, slot_id):
    """Plate not found: search Vehicles by slot_id instead."""
    for record in vehicles.values():
        if record["slot_id"] == slot_id:
            return record
    return None


def exception_case_3_payment_failed():
    """Keep barrier closed and ask the driver to retry or change method."""
    flash(
        "Payment failed. Barrier stays closed. "
        "Please retry the transaction or use another payment method "
        "(M-Pesa, card, or cash).",
        "error",
    )


def exception_case_4_record_failed():
    """Payment went through but the Transactions insert failed."""
    flash(
        "Payment succeeded, but the system failed to record it. "
        "Show proof of payment. A supervisor must scan/select their ID, "
        "then the attendant logs the override.",
        "error",
    )


def exception_case_5_barrier_failed():
    flash(
        "Barrier failed to open after valid, recorded payment. "
        "Attendant has been alerted. Use an alternate exit, and log an override "
        "so a supervisor/manager can arrange repair.",
        "error",
    )




def slot_allocation(conn, plate_number, entry_time, slot_id):
    """
    1. Receive plate_number and entry_time
    2-3. Assign the free slot_id
    4. Create a Vehicles row
    5. Set ParkingSlots.status = occupied
    6. Display refresh happens when we redirect to the slot board
    """
    conn.execute(
        "INSERT INTO Vehicles (plate_number, entry_time, slot_id) VALUES (?, ?, ?)",
        (plate_number, format_time(entry_time), slot_id),
    )
    conn.execute(
        "UPDATE ParkingSlots SET status = 'occupied' WHERE slot_id = ?",
        (slot_id,),
    )


def admit_waiting_queue(conn):
    """When a bay becomes free, the first waiting car is allocated (FIFO)."""
    admitted = []
    while waiting_queue:
        slots = get_slots_list(conn)
        slot_id = find_first_free_slot(slots)
        if slot_id is None:
            break
        plate = waiting_queue.popleft()
        slot_allocation(conn, plate, now(), slot_id)
        admitted.append((plate, slot_id))
    return admitted



def exit_barrier_control(conn, vehicle_id, slot_id):
    """
    After payment is recorded:
    2. Open barrier for the vehicle
    3. Remove the Vehicles row
    4. Set the slot back to free
    5. Display refresh happens on redirect to the slot board
    """

    conn.execute("DELETE FROM Vehicles WHERE vehicle_id = ?", (vehicle_id,))
    conn.execute(
        "UPDATE ParkingSlots SET status = 'free' WHERE slot_id = ?",
        (slot_id,),
    )
    return admit_waiting_queue(conn)



@app.route("/")
def home():
    """Module 2: Slot Monitoring & Display."""
    conn = get_connection()
    slots = get_slots_list(conn)
    vehicles = get_vehicles_map(conn)
    conn.close()
    free_count = sum(1 for s in slots if s["status"] == "free")
    return render_template(
        "home.html",
        slots=slots,
        parked=list(vehicles.values()),
        free_count=free_count,
        waiting=list(waiting_queue),
    )


@app.route("/entry", methods=["GET", "POST"])
def entry():
    """Module 1: Entry Lane Control, then Module 3 if a slot is free."""
    if request.method == "POST":
        plate = request.form.get("plate_number", "").strip().upper()
        demo_hours = request.form.get("demo_hours", "0").strip() or "0"

        if not plate:
            flash("Please enter a plate number.", "error")
            return redirect(url_for("entry"))

        conn = get_connection()
        vehicles = get_vehicles_map(conn)
        if plate in vehicles:
            conn.close()
            flash("That vehicle is already parked.", "error")
            return redirect(url_for("entry"))
        if plate in waiting_queue:
            conn.close()
            flash("That vehicle is already in the waiting queue.", "error")
            return redirect(url_for("entry"))

        try:
            extra = float(demo_hours)
        except ValueError:
            extra = 0

        entry_time = now() - timedelta(hours=extra)

    
        slots = get_slots_list(conn)
        slot_id = find_first_free_slot(slots)

        if slot_id is None:
            conn.close()
            exception_case_1_lot_full(plate)
            return redirect(url_for("home"))

        slot_allocation(conn, plate, entry_time, slot_id)
        conn.commit()
        conn.close()
        flash(f"Entry allowed. {plate} assigned to slot {slot_id}.", "success")
        return redirect(url_for("home"))

    return render_template("entry.html")


@app.route("/exit", methods=["GET", "POST"])
def exit_vehicle():
    """Module 4: Duration & Fee Computation."""
    if request.method == "POST":
        plate = request.form.get("plate_number", "").strip().upper()
        slot_search = request.form.get("slot_id", "").strip()

        conn = get_connection()
        vehicles = get_vehicles_map(conn)
        vehicle = vehicles.get(plate) if plate else None

        if vehicle is None and slot_search:
            try:
                slot_id = int(slot_search)
            except ValueError:
                slot_id = None
            if slot_id is not None:
                vehicle = exception_case_2_find_by_slot(vehicles, slot_id)
                if vehicle:
                    plate = vehicle["plate_number"]

        if vehicle is None:
            conn.close()
            flash(
                "Vehicle record not found by plate number. "
                "Search Vehicles by slot_id instead.",
                "error",
            )
            return redirect(url_for("exit_vehicle"))

        entry_time = parse_time(vehicle["entry_time"])
        exit_time = now()
        duration = exit_time - entry_time
        duration_hours = duration.total_seconds() / 3600
        fee = lookup_fee_from_rates(conn, duration_hours)
        conn.close()

        session["pending_exit"] = {
            "vehicle_id": vehicle["vehicle_id"],
            "plate_number": plate,
            "slot_id": vehicle["slot_id"],
            "entry_time": vehicle["entry_time"],
            "exit_time": format_time(exit_time),
            "duration_text": str(duration),
            "fee": fee,
        }
        return redirect(url_for("payment"))

    return render_template("exit.html")


@app.route("/payment", methods=["GET", "POST"])
def payment():
    """Module 5: Payment Collection. Barrier opens only after a recorded payment."""
    pending = session.get("pending_exit")
    if not pending:
        flash("No vehicle is waiting to pay. Start from Exit first.", "error")
        return redirect(url_for("exit_vehicle"))

    if request.method == "POST":
        action = request.form.get("action")
        method = request.form.get("payment_method")
        mpesa_phone = request.form.get("mpesa_phone", "").strip()

        if action == "fail":
            exception_case_3_payment_failed()
            return redirect(url_for("payment"))

        if not method:
            flash("Choose a payment method: M-Pesa, card, or cash.", "error")
            return redirect(url_for("payment"))

        if method == "M-Pesa" and not mpesa_phone:
            flash("Enter the M-Pesa phone number so the STK prompt can be sent.", "error")
            return redirect(url_for("payment"))

        conn = get_connection()
        try:
            if action == "record_fail":
                raise sqlite3.Error("simulated recording failure")
            conn.execute(
                """
                INSERT INTO Transactions
                    (vehicle_id, plate_number, slot_id, exit_time, amount_paid, payment_method)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    pending["vehicle_id"],
                    pending["plate_number"],
                    pending["slot_id"],
                    pending["exit_time"],
                    pending["fee"],
                    method,
                ),
            )
            conn.commit()
        except sqlite3.Error:
            conn.close()
            exception_case_4_record_failed()
            return redirect(url_for("override"))

        conn.close()

        paid = dict(pending)
        paid["payment_method"] = method
        paid["mpesa_phone"] = mpesa_phone
        session["paid_exit"] = paid
        session.pop("pending_exit", None)

        if action == "barrier_fail":
            exception_case_5_barrier_failed()
            return redirect(url_for("override"))

        return redirect(url_for("barrier"))

    return render_template("payment.html", pending=pending)


@app.route("/barrier")
def barrier():
    """Module 6 continues: open barrier only after Module 5 recorded payment."""
    paid = session.get("paid_exit")
    if not paid:
        flash("No confirmed payment found. Barrier remains closed.", "error")
        return redirect(url_for("home"))

    conn = get_connection()
    admitted = exit_barrier_control(conn, paid["vehicle_id"], paid["slot_id"])
    conn.commit()
    conn.close()
    session.pop("paid_exit", None)

    messages = [
        f"Payment received. Barrier Open for {paid['plate_number']}.",
        f"Slot {paid['slot_id']} is now free.",
    ]
    for plate, slot_id in admitted:
        messages.append(f"Waiting car {plate} was allocated slot {slot_id}.")
    flash(" ".join(messages), "success")
    return render_template("barrier.html", paid=paid, admitted=admitted)


@app.route("/override", methods=["GET", "POST"])
def override():
    """
    Exception cases 4, 5 and 6:
    supervisor confirms, log Overrides, then open the barrier
    (fee calculation can be bypassed, e.g. ambulance).
    """
    conn = get_connection()
    staff = [dict(row) for row in conn.execute("SELECT * FROM Staff").fetchall()]

    if request.method == "POST":
        plate = request.form.get("plate_number", "").strip().upper()
        staff_id = request.form.get("staff_id")
        reason = request.form.get("reason", "").strip()
        payment_ref = request.form.get("payment_ref", "").strip()

        if not plate or not staff_id or not reason:
            conn.close()
            flash("Plate number, staff member, and reason are required.", "error")
            return redirect(url_for("override"))

        vehicles = get_vehicles_map(conn)
        vehicle = vehicles.get(plate)
        vehicle_id = vehicle["vehicle_id"] if vehicle else None
        slot_id = vehicle["slot_id"] if vehicle else None

        full_reason = reason
        if payment_ref:
            full_reason += f" | payment ref: {payment_ref}"

        conn.execute(
            """
            INSERT INTO Overrides (vehicle_id, plate_number, staff_id, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (vehicle_id, plate, int(staff_id), full_reason, format_time(now())),
        )

        admitted = []
        if vehicle:
            admitted = exit_barrier_control(conn, vehicle_id, slot_id)

        conn.commit()
        conn.close()
        extra = ""
        if admitted:
            extra = " Waiting cars were then allocated free slots."
        flash(f"Override confirmed. Barrier Open for {plate}.{extra}", "success")
        session.pop("pending_exit", None)
        session.pop("paid_exit", None)
        return redirect(url_for("home"))

    conn.close()
    pending = session.get("pending_exit") or session.get("paid_exit")
    return render_template("override.html", staff=staff, pending=pending)


@app.route("/reports", methods=["GET", "POST"])
def reports():
    """Module 8: Administrative Reporting."""
    period = request.form.get("period", request.args.get("period", "daily"))
    end = now()
    if period == "weekly":
        start = end - timedelta(days=7)
        label = "Last 7 days"
    elif period == "monthly":
        start = end - timedelta(days=30)
        label = "Last 30 days"
    else:
        start = end.replace(hour=0, minute=0, second=0)
        label = "Today"

    start_text = format_time(start)
    end_text = format_time(end)

    conn = get_connection()
    transactions = [
        dict(row)
        for row in conn.execute(
            """
            SELECT * FROM Transactions
            WHERE exit_time >= ? AND exit_time <= ?
            ORDER BY exit_time DESC
            """,
            (start_text, end_text),
        ).fetchall()
    ]
    overrides = [
        dict(row)
        for row in conn.execute(
            """
            SELECT Overrides.*, Staff.name, Staff.role
            FROM Overrides
            JOIN Staff ON Staff.staff_id = Overrides.staff_id
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp DESC
            """,
            (start_text, end_text),
        ).fetchall()
    ]
    conn.close()

    total_revenue = sum(t["amount_paid"] for t in transactions)
    return render_template(
        "reports.html",
        period=period,
        label=label,
        transactions=transactions,
        overrides=overrides,
        total_revenue=total_revenue,
        total_vehicles=len(transactions),
        total_overrides=len(overrides),
    )


@app.route("/reports/export")
def reports_export():
    """Module 8: downloadable CSV for the accountant/auditor."""
    period = request.args.get("period", "daily")
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT transaction_id, plate_number, slot_id, exit_time, amount_paid, payment_method
        FROM Transactions
        ORDER BY exit_time DESC
        """
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["transaction_id", "plate_number", "slot_id", "exit_time", "amount_paid", "payment_method"]
    )
    for row in rows:
        writer.writerow(list(row))

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=parking-report-{period}.csv"},
    )


if __name__ == "__main__":
    app.run(debug=True)

# DSA Task 1 — Modern Parking System (Kenya)

Student website for a class assignment: **HTML/CSS frontend**, **Python (Flask) backend**, **SQLite database**.

The three written parts of the task are in `docs/`:

1. [Algorithms](docs/01_ALGORITHMS.md)
2. [Data structures](docs/02_DATA_STRUCTURES.md)
3. [Dynamic database design](docs/03_DATABASE_DESIGN.md)

## How to run

In a terminal, from this folder:

```
python -m pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in a browser.

`parking.db` is created automatically the first time the app starts.

## How to use it

1. **Slots** — board of 12 bays (green = free, red = occupied).
2. **Entry** — type a plate. If a bay is free, the car is parked. If the lot is full, entry is denied and the plate goes on the waiting queue.
3. **Exit & Pay** — look up the car, see duration and fee, then pay.
4. **Payment** — M-Pesa, card, or cash. The barrier opens only after payment is confirmed. M-Pesa asks for a phone number (demo STK, not a live Safaricom API).
5. **Override** — supervisor path for failed recording, stuck barrier, or emergency (for example an ambulance).
6. **Reports** — daily / weekly / monthly totals, plus CSV export.

On the entry form, **Hours already parked** is only for testing fees quickly (try `3` to get KES 100).

## Project files

| File | Role |
|---|---|
| `app.py` | Backend: the 8 modules |
| `db.py` | SQLite tables and starter data |
| `templates/` | HTML pages |
| `static/style.css` | Simple styling |
| `docs/` | Assignment write-ups |

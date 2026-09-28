# Part (c): Design of the Dynamic Database

## Design principle

The database is dynamic because the **table structure (columns) is designed once**, while **rows are added, updated, or removed** as vehicles enter, pay, and leave. The schema does not need to be redesigned for each car.

Normalization keeps each kind of fact in its own table:

- bays in `ParkingSlots`
- cars currently parked in `Vehicles`
- completed payments in `Transactions`
- fee bands in `Rates`
- employees in `Staff`
- manual barrier openings in `Overrides`

Foreign keys link those tables without copying names and roles onto every row.


## Tables

### ParkingSlots

| Field | Type | Key |
|---|---|---|
| slot_id | INTEGER | PK |
| status | TEXT (`free` / `occupied`) | |

One row per physical bay. Status is updated on allocation and on exit.

### Vehicles

| Field | Type | Key |
|---|---|---|
| vehicle_id | INTEGER | PK (auto) |
| plate_number | TEXT | |
| entry_time | TEXT (datetime) | |
| slot_id | INTEGER | FK → ParkingSlots.slot_id |

This table holds cars **currently in the lot**. After a successful exit the row is deleted, matching the Exit Barrier algorithm.

### Transactions

| Field | Type | Key |
|---|---|---|
| transaction_id | INTEGER | PK (auto) |
| vehicle_id | INTEGER | recorded id, not a live FK |
| plate_number | TEXT | |
| slot_id | INTEGER | |
| exit_time | TEXT (datetime) | |
| amount_paid | REAL | |
| payment_method | TEXT (`M-Pesa` / `card` / `cash`) | |


### Rates

| Field | Type | Key |
|---|---|---|
| rate_id | INTEGER | PK (auto) |
| max_hours | REAL | |
| fee | REAL | |

Management can change fees by editing this table, without rewriting the website.

Seeded bands (Kenya shillings):

| max_hours | fee |
|---|---|
| 0.5 | 0 |
| 2 | 50 |
| 4 | 100 |
| 6 | 300 |
| 10 | 500 |

### Staff

| Field | Type | Key |
|---|---|---|
| staff_id | INTEGER | PK (auto) |
| name | TEXT | |
| role | TEXT (`attendant` / `supervisor` / `manager`) | |

### Overrides

| Field | Type | Key |
|---|---|---|
| override_id | INTEGER | PK (auto) |
| vehicle_id | INTEGER | may be empty if the car row is already gone |
| plate_number | TEXT | |
| staff_id | INTEGER | FK → Staff.staff_id |
| reason | TEXT | |
| timestamp | TEXT (datetime) | |

---

## Relationships

- One ParkingSlot is used by many Vehicles over time (one-to-many). At one moment a slot is free or holds one current vehicle.
- One parked visit produces at most one Transaction when the driver exits and pays.
- One Staff member can record many Overrides (one-to-many).
- A Vehicle visit has an Override only in exception cases.

## Why Staff and Overrides are separate

Staff name and role should not be typed on every override row. If an attendant is hired or leaves, only the Staff table changes. Old override rows still point at `staff_id` and remain usable for audit.

## What “dynamic” means in this project

- New vehicle rows appear at entry.
- Slot status flips between free and occupied.
- Transaction rows are appended at payment.
- Override rows are appended only when a supervisor bypasses the normal path.
- Rate rows can be changed if the parking company updates prices.

The column list stays the same.

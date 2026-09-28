# Part (b): Data Structures and Reasons for Their Use


| Module / situation | Data structure | How it is used in the program | Reason |
|---|---|---|---|
| Slot monitoring and display | **Array / List** | `get_slots_list()` loads every bay into a Python list, in `slot_id` order. The home page loops through that list. | The number of bays is fixed (12 in this demo) and they are numbered. A list maps onto the physical layout and lets the program read any slot by position. |
| Vehicle lookup at entry and exit | **Hash map / Dictionary** | `get_vehicles_map()` builds `{plate_number: vehicle_record}` from the Vehicles table. Exit looks up one car with `vehicles.get(plate)`. | The attendant needs one specific car, not a scan of every row on the screen. A dictionary finds that record in constant time. |
| Cars waiting when the lot is full | **Queue** (`collections.deque`) | `waiting_queue`. Case 1 denies immediate entry and `append()`s the plate. When a car leaves, `popleft()` gives the first waiting plate a slot. | First car that started waiting should be the first allocated a bay (FIFO). |
| Single-lane, dead-end bays | **Stack** | Not used as the main structure. | A stack would be LIFO: last car in is first car out. That fits nose-to-tail bays, but this client wants independently accessible slots, so a stack is only considered, not implemented. |

## Why not keep everything in one list?

A list of parked cars would work for a tiny lot, but exit would have to check each car until the plate matched. A dictionary avoids that loop. The list is still the right tool for the slot board, because we always show every bay, in order.

## How the structures work with SQLite

SQLite is the lasting store (the database). The list, dictionary, and queue are used in memory while a request is handled:

1. Read slots and parked cars from SQLite into a list and a dictionary.
2. Use those structures in the algorithm (find a free slot, look up a plate).
3. Write the result back to SQLite.

The waiting queue is only in memory. If the server is restarted, waiting cars are lost. A later version could store the queue in a table. For this assignment the queue still shows the FIFO idea required by the task.

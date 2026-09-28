# Part (a): Algorithms for Each Module


## 1. Entry Lane Control Module

```
START
1. Driver arrives at entrance
2. Prompt driver to input/scan plate number
3. Record current system time as entry_time
4. Check ParkingSlots table for any slot with status = "free"
5. IF no free slot exists:
     Trigger Exception Handling Module (Case 1)
6. ELSE:
     Pass plate_number, entry_time to Slot Allocation Module
END
```


## 2. Slot Monitoring & Display Module

```
START
1. Connect to ParkingSlots table
2. Retrieve all rows (slot_id, status)
3. FOR each slot in the list:
     Display slot_id and its status (free/occupied) on screen
4. Refresh this display whenever a slot's status changes
END
```


## 3. Slot Allocation Module

```
START
1. Receive plate_number and entry_time from Entry Lane Control Module
2. Search ParkingSlots table for first slot where status = "free"
3. Assign that slot_id to this vehicle
4. Create new row in Vehicles table:
     (vehicle_id, plate_number, entry_time, slot_id)
5. Update ParkingSlots table:
     SET status = "occupied" WHERE slot_id = assigned slot
6. Trigger Slot Monitoring & Display Module to refresh
END
```


## 4. Duration & Fee Computation Module

```
START
1. Triggered when driver requests to exit
2. Retrieve entry_time for that vehicle from Vehicles table
     IF vehicle record not found by plate number:
       Trigger Exception Handling Module (Case 2)
3. Get current system time as exit_time
4. Calculate duration = exit_time - entry_time
5. Look up applicable fee from Rates table based on duration:
     IF duration <= 30 minutes: fee = 0
     ELSE IF duration <= 2 hours: fee = 50
     ELSE IF duration <= 4 hours: fee = 100
     ELSE IF duration <= 6 hours: fee = 300
     ELSE: fee = 500
6. Pass fee amount to Payment Collection Module
END
```


## 5. Payment Collection Module

```
START
1. Receive fee amount from Duration & Fee Computation Module
2. Display amount due to driver
3. Prompt driver to choose payment method: M-Pesa, card, or cash
4. WAIT for payment confirmation
5. IF payment fails:
     Trigger Exception Handling Module (Case 3)
6. IF payment succeeds:
     Create new row in Transactions table:
       (transaction_id, vehicle_id, plate_number, slot_id, exit_time, amount_paid, payment_method)
     IF system fails to record the transaction despite successful payment:
       Trigger Exception Handling Module (Case 4)
     ELSE:
       Pass control to Exit Barrier Control Module
END
```


M-Pesa is included as a real choice. This is a student demo, so it does not call Safaricom. The driver enters a phone number (as if an STK push was sent). Confirming payment is what allows the barrier to open.

---

## 6. Exit Barrier Control Module

```
START
1. Receive confirmation from Payment Collection Module
2. Open barrier (signal/display "Barrier Open")
3. IF barrier fails to open:
     Trigger Exception Handling Module (Case 5)
4. Remove vehicle's row from Vehicles table
5. Update ParkingSlots table:
     SET status = "free" WHERE slot_id = vehicle's former slot
6. Close barrier after car passes through
7. Trigger Slot Monitoring & Display Module to refresh
END
```


## 7. Exception Handling Module

```
START
1. IF no free slots available:
     Display "Sorry, parking lot full, no available spaces"
     Deny entry
     (Adjustment: also place the plate on a FIFO waiting queue.
      When a slot later becomes free, Slot Allocation runs for that car.)

2. IF vehicle record not found by plate number:
     Search Vehicles table by slot_id instead
     Retrieve matching vehicle record

3. IF payment fails:
     Keep barrier closed
     Prompt driver to retry transaction or use another payment method

4. IF payment succeeds BUT system fails to record it:
     Driver/attendant shows proof of payment
     Supervisor selects their staff record for verification
     Attendant logs: vehicle_id, staff_id, payment reference code,
       reason, timestamp into Overrides table
     Barrier opens once override is confirmed

5. IF barrier fails to open after valid, recorded payment:
     Alert attendant
     Attendant reports fault to supervisor/manager for repair
     Driver directed to use alternate exit
     (An override can still free the slot after the car uses another exit.)

6. IF emergency or system-wide outage occurs:
     Supervisor (or higher authority) authorizes override
     Fee Calculation Module is bypassed for this vehicle (e.g. ambulance)
     Log: vehicle_id, staff_id, reason, timestamp into Overrides table
     Barrier opens
END
```


## 8. Administrative Reporting Module

```
START
1. Attendant/manager/accountant selects a report period
   (daily, weekly, monthly)

2. Query Transactions table:
     Retrieve all rows where exit_time falls within selected period

3. Calculate total_revenue = SUM(amount_paid) for those rows

4. Calculate total_vehicles = COUNT(rows) for those rows

5. Query Overrides table:
     Retrieve all rows where timestamp falls within selected period

6. Calculate total_overrides = COUNT(rows) from Overrides
     List each override's reason, staff_id, and timestamp for review

7. Compile report containing:
     - Period covered
     - total_revenue
     - total_vehicles
     - total_overrides (with details)

8. Display report on screen for management

9. IF export requested:
     Generate downloadable CSV
END
```


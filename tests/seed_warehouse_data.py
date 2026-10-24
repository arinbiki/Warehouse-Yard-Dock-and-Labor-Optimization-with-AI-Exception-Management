"""
Database Seeder for Warehouse, Yard, Dock, and Labor Operations
Populates normalized master data across the 16 SQLite tables:
- Warehouses, Zones, Dock Doors, Yard Spots, Equipment
- Employees, Tasks, Trailers, Appointments, Outbound Orders, Waves, Exceptions
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.database import init_db, get_connection

def seed_database():
    print("Initializing warehouse operational database schema...")
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 1. Warehouse Master
        cursor.execute("""
            INSERT OR REPLACE INTO warehouses (warehouse_id, name, location, operating_start_hour, operating_end_hour)
            VALUES (?, ?, ?, ?, ?)
        """, ("WH-01", "Midwest Distribution Logistics Hub", "Joliet, IL (I-80 Corridor)", 6, 22))

        # 2. Zones (8 Zones)
        zones = [
            ("ZONE-REC", "WH-01", "Inbound Receiving Staging", "INBOUND_RECEIVING", 35, 12, 0.80, 20.0, 0, json.dumps(["FORKLIFT"])),
            ("ZONE-PUT", "WH-01", "Putaway Buffer Lane", "PUTAWAY", 40, 18, 0.85, 20.0, 0, json.dumps(["REACH_TRUCK"])),
            ("ZONE-FP-AMB", "WH-01", "Forward Pick Ambient Golden Zone", "FORWARD_PICK", 60, 42, 0.80, 21.0, 0, json.dumps(["ORDER_PICKER"])),
            ("ZONE-FP-COLD", "WH-01", "Forward Pick Cold Chain Vault", "COLD_STORAGE", 30, 20, 0.75, 4.0, 0, json.dumps(["ORDER_PICKER"])),
            ("ZONE-BULK", "WH-01", "High-Bay Reserve Bulk Racks", "BULK_STORAGE", 80, 62, 0.90, 20.0, 0, json.dumps(["REACH_TRUCK"])),
            ("ZONE-PACK", "WH-01", "Automated Packing & Taper Lines", "PACKING", 45, 32, 0.85, 20.0, 0, json.dumps(["CONVEYOR"])),
            ("ZONE-STAGE-OUT", "WH-01", "Outbound Staging Lane", "STAGING", 50, 28, 0.80, 20.0, 0, json.dumps(["PALLET_JACK"])),
            ("ZONE-HAZ", "WH-01", "Hazmat Class 3 Flammables Bunker", "HAZMAT", 15, 6, 0.70, 18.0, 1, json.dumps(["FORKLIFT"]))
        ]
        for z in zones:
            cursor.execute("""
                INSERT OR REPLACE INTO zones (zone_id, warehouse_id, name, zone_type, capacity_units, current_occupancy, congestion_threshold, temperature_c, is_hazmat_certified, required_equipment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, z)

        # 3. Dock Doors (24 Doors)
        for i in range(1, 25):
            door_id = f"DOCK-{i:02d}"
            direction = "INBOUND" if i <= 12 else "OUTBOUND"
            has_reefer = i in [1, 2, 3, 4, 13, 14]
            has_hazmat = i in [11, 12, 23, 24]
            status = "MAINTENANCE" if i == 8 else ("OCCUPIED" if i in [3, 12, 19] else "ACTIVE")
            cur_trailer = f"TR-{1000+i}" if status == "OCCUPIED" else None
            supported = json.dumps(["DRY_VAN_53", "REEFER_53"]) if has_reefer else json.dumps(["DRY_VAN_53"])

            cursor.execute("""
                INSERT OR REPLACE INTO dock_doors (door_id, warehouse_id, name, direction, supported_trailers, has_leveler, has_reefer_seal, has_hazmat_exhaust, avg_processing_time_min, status, current_trailer_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (door_id, "WH-01", f"Dock Door {i:02d}", direction, supported, 1, 1 if has_reefer else 0, 1 if has_hazmat else 0, 85 if has_reefer else 60, status, cur_trailer))

        # 4. Yard Spots (80 Spots)
        for i in range(1, 81):
            row = chr(65 + (i - 1) // 20)
            num = ((i - 1) % 20) + 1
            spot_id = f"SPOT-{row}{num:02d}"
            is_reefer = (row == 'B') # Row B has shore power 480V
            is_hazmat = (row == 'C') # Row C is hazmat containment
            status = "OCCUPIED" if random.random() < 0.65 else "EMPTY"
            cur_tr = f"TR-YARD-{i:03d}" if status == "OCCUPIED" else None
            distances = json.dumps({"DOCK-01": 35.0, "DOCK-04": 25.0, "DOCK-12": 55.0})

            cursor.execute("""
                INSERT OR REPLACE INTO yard_spots (spot_id, warehouse_id, name, zone_coord_x, zone_coord_y, has_reefer_plug, is_hazmat_safe, status, current_trailer_id, distance_to_doors)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (spot_id, "WH-01", f"Yard Spot {spot_id[5:]}", float(num * 10), 50.0, 1 if is_reefer else 0, 1 if is_hazmat else 0, status, cur_tr, distances))

        # 5. Equipment (12 Units)
        eq_units = [
            ("FORK-01", "WH-01", "FORKLIFT", 0.95, "AVAILABLE", "ZONE-REC", "EMP-101"),
            ("FORK-02", "WH-01", "FORKLIFT", 0.40, "CHARGING", "ZONE-REC", None),
            ("REACH-01", "WH-01", "REACH_TRUCK", 0.88, "AVAILABLE", "ZONE-PUT", "EMP-102"),
            ("REACH-02", "WH-01", "REACH_TRUCK", 0.82, "AVAILABLE", "ZONE-BULK", None),
            ("PICKER-01", "WH-01", "ORDER_PICKER", 0.92, "AVAILABLE", "ZONE-FP-AMB", "EMP-103"),
            ("PICKER-02", "WH-01", "ORDER_PICKER", 0.87, "AVAILABLE", "ZONE-FP-AMB", "EMP-104"),
            ("PICKER-03", "WH-01", "ORDER_PICKER", 0.90, "AVAILABLE", "ZONE-FP-COLD", "EMP-105"),
            ("HOSTLER-01", "WH-01", "YARD_HOSTLER", 0.98, "AVAILABLE", "YARD-MAIN", "EMP-108"),
            ("HOSTLER-02", "WH-01", "YARD_HOSTLER", 0.94, "AVAILABLE", "YARD-MAIN", None),
            ("PALLET-01", "WH-01", "PALLET_JACK", 0.75, "AVAILABLE", "ZONE-STAGE-OUT", None)
        ]
        for eq in eq_units:
            cursor.execute("""
                INSERT OR REPLACE INTO equipment (equipment_id, warehouse_id, equipment_type, battery_level, status, current_zone_id, assigned_operator_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, eq)

        # 6. Employees (10 Key Operators)
        employees = [
            ("EMP-101", "Marcus Vance", "SHIFT-MORNING", json.dumps(["FORKLIFT", "COLD_CHAIN"]), json.dumps(["OSHA_FORKLIFT"]), 1.05, "ZONE-REC", None, 0.35, 1, 0.0),
            ("EMP-102", "Elena Rostova", "SHIFT-MORNING", json.dumps(["REACH_TRUCK", "HAZMAT"]), json.dumps(["REACH_TRUCK_CERT"]), 1.02, "ZONE-PUT", None, 0.40, 1, 0.0),
            ("EMP-103", "David Kim", "SHIFT-MORNING", json.dumps(["ORDER_PICKER", "RF_SCANNER"]), json.dumps(["ORDER_PICKER_CERT"]), 1.15, "ZONE-FP-AMB", None, 0.45, 1, 1.5),
            ("EMP-104", "Sarah Jenkins", "SHIFT-MORNING", json.dumps(["ORDER_PICKER", "RF_SCANNER"]), json.dumps(["ORDER_PICKER_CERT"]), 1.10, "ZONE-FP-AMB", None, 0.42, 1, 1.0),
            ("EMP-105", "Jamal Washington", "SHIFT-MORNING", json.dumps(["ORDER_PICKER", "COLD_CHAIN"]), json.dumps(["COLD_CHAIN_PPE"]), 1.00, "ZONE-FP-COLD", None, 0.48, 1, 0.0),
            ("EMP-106", "Carlos Mendez", "SHIFT-MORNING", json.dumps(["PACKING", "TAPER"]), json.dumps(["PACKING_SAFETY"]), 1.08, "ZONE-PACK", None, 0.30, 1, 0.0),
            ("EMP-107", "Aisha Al-Mansoor", "SHIFT-MORNING", json.dumps(["PACKING", "QA"]), json.dumps(["QUALITY_INSPECTOR"]), 1.12, "ZONE-PACK", None, 0.28, 1, 0.0),
            ("EMP-108", "Travis Scott", "SHIFT-MORNING", json.dumps(["YARD_HOSTLER", "CDL"]), json.dumps(["CDL_CLASS_A"]), 1.05, "YARD-MAIN", None, 0.50, 1, 2.0),
            ("EMP-109", "Linda Chen", "SHIFT-MORNING", json.dumps(["SUPERVISOR", "SOP_LEAD"]), json.dumps(["ALL_CERTS"]), 1.20, "ZONE-STAGE-OUT", None, 0.25, 1, 0.0),
            ("EMP-110", "Kevin O'Connor", "SHIFT-MORNING", json.dumps(["ORDER_PICKER"]), json.dumps(["ORDER_PICKER_CERT"]), 0.95, "ZONE-FP-AMB", None, 0.55, 1, 0.0)
        ]
        for emp in employees:
            cursor.execute("""
                INSERT OR REPLACE INTO employees (employee_id, name, shift_id, skills, equipment_certifications, productivity_index, current_zone_id, current_task_id, fatigue_level, is_available, overtime_hours_accumulated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, emp)

        # 7. Trailers (Active Inbound & Outbound)
        trailers = [
            ("TR-402", "SWIFT", "Swift Logistics", "DRY_VAN_53", 53, 0, None, 0, None, "AT_DOCK", "SPOT-A04", "DOCK-04", (datetime.utcnow() - timedelta(hours=1.5)).isoformat(), (datetime.utcnow() + timedelta(hours=2.0)).isoformat(), 2.0, 75.0, "URGENT", "Electronics & Retail", 26),
            ("TR-908", "JB_HUNT", "J.B. Hunt", "REEFER_53", 53, 1, 3.5, 0, None, "IN_YARD", "SPOT-B12", None, (datetime.utcnow() - timedelta(hours=3.0)).isoformat(), (datetime.utcnow() + timedelta(hours=4.0)).isoformat(), 2.0, 75.0, "HIGH", "Perishable Dairy", 24),
            ("TR-102", "SCHNEIDER", "Schneider National", "DRY_VAN_53", 53, 0, None, 0, None, "IN_YARD", "SPOT-A10", None, (datetime.utcnow() - timedelta(hours=0.8)).isoformat(), (datetime.utcnow() + timedelta(hours=5.0)).isoformat(), 2.0, 75.0, "STANDARD", "Apparel & Footwear", 28),
            ("TR-550", "WERNER", "Werner Enterprises", "REEFER_53", 53, 1, -18.0, 0, None, "IN_YARD", "SPOT-B04", None, (datetime.utcnow() - timedelta(hours=1.0)).isoformat(), (datetime.utcnow() + timedelta(hours=3.5)).isoformat(), 2.0, 75.0, "HIGH", "Frozen Seafood", 22)
        ]
        for tr in trailers:
            cursor.execute("""
                INSERT OR REPLACE INTO trailers (trailer_id, carrier_id, carrier_name, trailer_type, length_ft, is_refrigerated, target_temperature_c, is_hazmat, hazmat_class, status, current_spot_id, current_door_id, arrival_time, expected_departure_time, free_time_hours, detention_rate_per_hour, priority, contents_summary, pallet_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, tr)

        # 8. Outbound Orders & Waves
        for i in range(1, 5):
            wid = f"WAVE-2026-0{i}"
            order_ids = [f"ORD-{i*100 + j}" for j in range(1, 21)]
            cursor.execute("""
                INSERT OR REPLACE INTO waves (wave_id, name, order_ids, zone_ids, picking_method, planned_release_time, est_duration_minutes, labor_hours_required, priority, status, cut_off_risk_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (wid, f"Priority Outbound Wave {i}", json.dumps(order_ids), json.dumps(["ZONE-FP-AMB", "ZONE-FP-COLD"]), "BATCH_PICKING" if i in [1, 2] else "ZONE_PICKING", (datetime.utcnow() + timedelta(hours=i*1.2)).isoformat(), 75, 4.5, "HIGH" if i == 1 else "STANDARD", "IN_PROGRESS" if i == 1 else "PLANNED", 0.05 * i))

        # 9. Exception Record
        cursor.execute("""
            INSERT OR REPLACE INTO exceptions (exception_id, category, severity, title, description, detected_at, status, impacted_entities, root_cause_hypotheses, recommended_actions, selected_action)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "EXC-8821",
            "DOCK",
            "HIGH",
            "Door DOCK-08 Hydraulic Interlock Fault",
            "Dock leveler interlock alarm tripped during trailer uncoupling; door taken offline.",
            datetime.utcnow().isoformat(),
            "IN_PROGRESS",
            json.dumps({"root_entity": "DOCK-08", "queued_trailers": ["TR-908", "TR-102"], "financial_risk_usd": 225.0}),
            json.dumps([{"hypothesis": "Hydraulic solenoid pressure sensor failure", "confidence_score": 0.92}]),
            json.dumps([{"action_id": "ACT-DIVERT-01", "description": "Divert trailer TR-908 to Flex Door DOCK-14", "cost_usd": 25.0}]),
            "ACT-DIVERT-01"
        ))

        conn.commit()
        print("Master operational data seeded successfully into warehouse_operations.db!")
    finally:
        conn.close()

if __name__ == "__main__":
    seed_database()

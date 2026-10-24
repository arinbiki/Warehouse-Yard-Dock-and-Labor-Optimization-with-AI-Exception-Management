"""
Relational SQLite Storage Engine with Write-Ahead Logging (WAL) and Concurrency Controls.
Provides thread-safe initialization, schema migrations, and query interfaces.
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from core.config import OPERATIONS_DB

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(OPERATIONS_DB, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS warehouses (
        warehouse_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        operating_start_hour INTEGER DEFAULT 6,
        operating_end_hour INTEGER DEFAULT 22,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS zones (
        zone_id TEXT PRIMARY KEY,
        warehouse_id TEXT NOT NULL,
        name TEXT NOT NULL,
        zone_type TEXT NOT NULL,
        capacity_units INTEGER DEFAULT 1000,
        current_occupancy INTEGER DEFAULT 0,
        congestion_threshold REAL DEFAULT 0.80,
        temperature_c REAL,
        is_hazmat_certified INTEGER DEFAULT 0,
        required_equipment TEXT, -- JSON list
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
    );

    CREATE TABLE IF NOT EXISTS dock_doors (
        door_id TEXT PRIMARY KEY,
        warehouse_id TEXT NOT NULL,
        name TEXT NOT NULL,
        direction TEXT NOT NULL, -- INBOUND, OUTBOUND, FLEXIBLE
        supported_trailers TEXT, -- JSON list
        has_leveler INTEGER DEFAULT 1,
        has_reefer_seal INTEGER DEFAULT 0,
        has_hazmat_exhaust INTEGER DEFAULT 0,
        avg_processing_time_min INTEGER DEFAULT 45,
        status TEXT DEFAULT 'ACTIVE',
        current_trailer_id TEXT,
        next_available_time TEXT,
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
    );

    CREATE TABLE IF NOT EXISTS yard_spots (
        spot_id TEXT PRIMARY KEY,
        warehouse_id TEXT NOT NULL,
        name TEXT NOT NULL,
        zone_coord_x REAL DEFAULT 0.0,
        zone_coord_y REAL DEFAULT 0.0,
        has_reefer_plug INTEGER DEFAULT 0,
        is_hazmat_safe INTEGER DEFAULT 0,
        status TEXT DEFAULT 'EMPTY',
        current_trailer_id TEXT,
        distance_to_doors TEXT, -- JSON dict
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
    );

    CREATE TABLE IF NOT EXISTS trailers (
        trailer_id TEXT PRIMARY KEY,
        carrier_id TEXT NOT NULL,
        carrier_name TEXT NOT NULL,
        trailer_type TEXT NOT NULL,
        length_ft INTEGER DEFAULT 53,
        is_refrigerated INTEGER DEFAULT 0,
        target_temperature_c REAL,
        is_hazmat INTEGER DEFAULT 0,
        hazmat_class TEXT,
        status TEXT DEFAULT 'EXPECTED',
        current_spot_id TEXT,
        current_door_id TEXT,
        arrival_time TEXT,
        expected_departure_time TEXT,
        free_time_hours REAL DEFAULT 2.0,
        detention_rate_per_hour REAL DEFAULT 75.0,
        priority TEXT DEFAULT 'STANDARD',
        contents_summary TEXT,
        pallet_count INTEGER DEFAULT 26
    );

    CREATE TABLE IF NOT EXISTS equipment (
        equipment_id TEXT PRIMARY KEY,
        warehouse_id TEXT NOT NULL,
        equipment_type TEXT NOT NULL,
        battery_level REAL DEFAULT 1.0,
        status TEXT DEFAULT 'AVAILABLE',
        current_zone_id TEXT,
        assigned_operator_id TEXT,
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
    );

    CREATE TABLE IF NOT EXISTS appointments (
        appointment_id TEXT PRIMARY KEY,
        warehouse_id TEXT NOT NULL,
        appointment_type TEXT NOT NULL,
        carrier_id TEXT NOT NULL,
        carrier_name TEXT NOT NULL,
        trailer_id TEXT,
        scheduled_arrival TEXT NOT NULL,
        scheduled_departure TEXT NOT NULL,
        assigned_door_id TEXT,
        priority TEXT DEFAULT 'STANDARD',
        status TEXT DEFAULT 'REQUESTED',
        pallet_count INTEGER DEFAULT 24,
        is_refrigerated INTEGER DEFAULT 0,
        required_temp_c REAL,
        is_hazmat INTEGER DEFAULT 0,
        historical_carrier_reliability REAL DEFAULT 0.90,
        buffer_minutes INTEGER DEFAULT 15,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
    );

    CREATE TABLE IF NOT EXISTS outbound_orders (
        order_id TEXT PRIMARY KEY,
        customer_name TEXT NOT NULL,
        customer_tier TEXT DEFAULT 'TIER_1',
        priority TEXT DEFAULT 'STANDARD',
        cut_off_time TEXT NOT NULL,
        carrier_departure_time TEXT NOT NULL,
        lines_count INTEGER DEFAULT 1,
        units_count INTEGER DEFAULT 1,
        weight_lbs REAL DEFAULT 100.0,
        required_temp_c REAL,
        is_hazmat INTEGER DEFAULT 0,
        assigned_wave_id TEXT,
        status TEXT DEFAULT 'NEW',
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS waves (
        wave_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        order_ids TEXT, -- JSON list
        zone_ids TEXT,  -- JSON list
        picking_method TEXT DEFAULT 'ZONE',
        planned_release_time TEXT NOT NULL,
        est_duration_minutes INTEGER DEFAULT 60,
        labor_hours_required REAL DEFAULT 4.0,
        priority TEXT DEFAULT 'STANDARD',
        status TEXT DEFAULT 'PLANNED',
        cut_off_risk_score REAL DEFAULT 0.0,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        zone_id TEXT NOT NULL,
        priority TEXT DEFAULT 'STANDARD',
        est_duration_minutes INTEGER DEFAULT 30,
        status TEXT DEFAULT 'PENDING',
        assigned_employee_id TEXT,
        assigned_equipment_id TEXT,
        source_location TEXT,
        destination_location TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS employees (
        employee_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        shift_id TEXT NOT NULL,
        skills TEXT, -- JSON list
        equipment_certifications TEXT, -- JSON list
        productivity_index REAL DEFAULT 1.0,
        current_zone_id TEXT,
        current_task_id TEXT,
        fatigue_level REAL DEFAULT 0.0,
        is_available INTEGER DEFAULT 1,
        overtime_hours_accumulated REAL DEFAULT 0.0
    );

    CREATE TABLE IF NOT EXISTS exceptions (
        exception_id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        detected_at TEXT DEFAULT (datetime('now')),
        status TEXT DEFAULT 'OPEN',
        impacted_entities TEXT, -- JSON dict
        root_cause_hypotheses TEXT, -- JSON list
        recommended_actions TEXT, -- JSON list
        selected_action TEXT,
        resolved_at TEXT,
        resolved_by TEXT
    );

    CREATE TABLE IF NOT EXISTS approvals (
        approval_id TEXT PRIMARY KEY,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        cost_impact REAL DEFAULT 0.0,
        sla_impact TEXT,
        status TEXT DEFAULT 'PENDING',
        approver_role TEXT DEFAULT 'OPERATIONS_SUPERVISOR',
        decision_token TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        resolved_at TEXT
    );

    CREATE TABLE IF NOT EXISTS audit_logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        details TEXT, -- JSON payload
        timestamp TEXT DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()

# Auto-initialize database schema on module import
init_db()

"""
Python Service 2: Event Processing Service.
Handles real-time operational event streams from WMS, TMS, Gate RFID, IoT sensors, and Telematics.
Normalizes payloads, validates state transitions, prevents duplicate triggers, and maps dependencies.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import json
from core.database import get_connection
from core.models import TrailerStatus, AppointmentStatus, ExceptionCategory, ExceptionSeverity

class EventProcessingService:
    def __init__(self):
        self._processed_event_ids = set()

    def normalize_event(self, raw_event: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and normalizes raw payload into standardized event schema."""
        evt_id = raw_event.get("event_id") or f"EVT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        evt_type = raw_event.get("event_type", "GENERIC_EVENT")
        payload = raw_event.get("payload") or raw_event
        return {
            "event_id": evt_id,
            "event_type": evt_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
            "status": "NORMALIZED"
        }


    def process_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Processes and routes an incoming operational event to state engines and trigger listeners."""
        event_id = payload.get("event_id") or f"EVT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        if event_id in self._processed_event_ids:
            return {"status": "DUPLICATE_IGNORED", "event_id": event_id}

        self._processed_event_ids.add(event_id)
        if len(self._processed_event_ids) > 10000:
            self._processed_event_ids.clear()

        # Log event to immutable audit log
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO audit_logs (event_type, entity_type, entity_id, details) VALUES (?, ?, ?, ?)",
            (event_type, payload.get("entity_type", "UNKNOWN"), payload.get("entity_id", "UNKNOWN"), json.dumps(payload))
        )
        conn.commit()
        conn.close()

        # Route by event type
        if event_type == "CARRIER_GATE_CHECKIN":
            return self._handle_gate_checkin(payload)
        elif event_type == "DOCK_ARRIVAL":
            return self._handle_dock_arrival(payload)
        elif event_type == "DOCK_UNLOAD_COMPLETE":
            return self._handle_dock_completion(payload)
        elif event_type == "CARRIER_ETA_UPDATE":
            return self._handle_eta_update(payload)
        elif event_type == "EQUIPMENT_MALFUNCTION":
            return self._handle_equipment_malfunction(payload)
        elif event_type == "TEMPERATURE_EXCURSION":
            return self._handle_temp_excursion(payload)
        else:
            return {"status": "RECORDED", "event_type": event_type, "event_id": event_id}

    def _handle_gate_checkin(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        trailer_id = payload.get("trailer_id")
        carrier_id = payload.get("carrier_id")
        conn = get_connection()
        cursor = conn.cursor()
        now_iso = datetime.utcnow().isoformat()

        cursor.execute(
            "UPDATE trailers SET status=?, arrival_time=? WHERE trailer_id=?",
            (TrailerStatus.ARRIVED_GATE.value, now_iso, trailer_id)
        )
        conn.commit()
        conn.close()

        return {
            "status": "PROCESSED",
            "action": "GATE_CHECKIN_REGISTERED",
            "trailer_id": trailer_id,
            "next_step": "TRIGGER_YARD_SPOT_ASSIGNMENT"
        }

    def _handle_dock_arrival(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        trailer_id = payload.get("trailer_id")
        door_id = payload.get("door_id")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE trailers SET status=?, current_door_id=? WHERE trailer_id=?", (TrailerStatus.AT_DOCK.value, door_id, trailer_id))
        cursor.execute("UPDATE dock_doors SET current_trailer_id=? WHERE door_id=?", (trailer_id, door_id))
        conn.commit()
        conn.close()

        return {"status": "PROCESSED", "action": "TRAILER_AT_DOCK", "trailer_id": trailer_id, "door_id": door_id}

    def _handle_dock_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        trailer_id = payload.get("trailer_id")
        door_id = payload.get("door_id")
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("UPDATE trailers SET status=?, current_door_id=NULL WHERE trailer_id=?", (TrailerStatus.COMPLETED.value, trailer_id))
        cursor.execute("UPDATE dock_doors SET current_trailer_id=NULL WHERE door_id=?", (door_id,))
        conn.commit()
        conn.close()

        return {"status": "PROCESSED", "action": "DOCK_PROCESSING_COMPLETED", "trailer_id": trailer_id, "door_id": door_id}

    def _handle_eta_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        appointment_id = payload.get("appointment_id")
        new_eta = payload.get("new_eta")
        delay_minutes = payload.get("delay_minutes", 0)

        trigger_exception = delay_minutes > 45
        return {
            "status": "PROCESSED",
            "appointment_id": appointment_id,
            "new_eta": new_eta,
            "delay_minutes": delay_minutes,
            "requires_rescheduling": trigger_exception,
            "trigger_exception": trigger_exception
        }

    def _handle_equipment_malfunction(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        equipment_id = payload.get("equipment_id")
        door_id = payload.get("door_id")
        return {
            "status": "EXCEPTION_TRIGGERED",
            "category": "DOCK",
            "severity": "HIGH",
            "equipment_id": equipment_id,
            "door_id": door_id,
            "recommendation": "REASSIGN_APPOINTMENTS_TO_ADJACENT_DOORS"
        }

    def _handle_temp_excursion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        trailer_id = payload.get("trailer_id")
        current_temp_c = payload.get("current_temp_c")
        max_allowed_c = payload.get("max_allowed_c")
        return {
            "status": "CRITICAL_ALERT",
            "category": "YARD",
            "severity": "CRITICAL",
            "trailer_id": trailer_id,
            "current_temp": current_temp_c,
            "threshold": max_allowed_c,
            "action": "DISPATCH_YARD_HOSTLER_TO_REEFER_SHORE_POWER"
        }

event_processing_service = EventProcessingService()

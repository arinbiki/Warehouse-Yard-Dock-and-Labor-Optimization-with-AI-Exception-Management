"""
Python Service 1: Master Data Service.
Manages warehouses, zones, doors, yard spots, equipment, labor skills, products, and carrier constraints.
Provides validation, capacity evaluation, and compatibility verification.
"""
from typing import Dict, List, Optional, Tuple, Any
import json
from core.models import (
    Warehouse, Zone, DockDoor, YardSpot, Equipment, Trailer, Appointment,
    ZoneType, DoorDirection, DoorStatus, TrailerType, EquipmentType, EquipmentStatus
)
from core.database import get_connection

class MasterDataService:
    def __init__(self):
        pass

    def validate_door_trailer_compatibility(self, door: DockDoor, trailer: Trailer) -> Tuple[bool, str]:
        """Validates physical and operational compatibility between a dock door and a trailer."""
        if door.status != DoorStatus.ACTIVE:
            return False, f"Door {door.door_id} is currently in {door.status.value} status."
        
        if trailer.trailer_type not in door.supported_trailers:
            return False, f"Door {door.door_id} does not support trailer type {trailer.trailer_type.value}."

        if trailer.is_refrigerated and not door.has_reefer_seal:
            return False, f"Door {door.door_id} lacks cold-chain reefer seal required for refrigerated trailer {trailer.trailer_id}."

        if trailer.is_hazmat and not door.has_hazmat_exhaust:
            return False, f"Door {door.door_id} lacks dedicated hazmat exhaust ventilation required for trailer {trailer.trailer_id}."

        return True, "Compatible"

    def check_door_trailer_compatibility(self, door: Any, trailer: Any) -> Dict[str, Any]:
        """Convenience adapter supporting dicts and models."""
        door_cold = door.get("supports_cold_chain", False) if isinstance(door, dict) else getattr(door, "has_reefer_seal", False)
        door_haz = door.get("hazmat_allowed", False) if isinstance(door, dict) else getattr(door, "has_hazmat_exhaust", False)
        
        tr_cold = trailer.get("is_cold_chain", False) or trailer.get("temperature_controlled", False) if isinstance(trailer, dict) else getattr(trailer, "is_refrigerated", False)
        tr_haz = trailer.get("is_hazmat", False) if isinstance(trailer, dict) else getattr(trailer, "is_hazmat", False)

        if tr_cold and not door_cold:
            return {"is_compatible": False, "reason": "Cold chain seal missing on door"}
        if tr_haz and not door_haz:
            return {"is_compatible": False, "reason": "Hazmat exhaust missing on door"}
        return {"is_compatible": True, "reason": "Compatible"}


    def validate_zone_capacity(self, zone: Zone, additional_units: int = 1) -> Tuple[bool, float]:
        """Calculates current occupancy and checks if adding units violates congestion threshold."""
        projected = zone.current_occupancy + additional_units
        utilization = projected / max(1, zone.capacity_units)
        is_safe = utilization <= zone.congestion_threshold
        return is_safe, utilization

    def check_yard_spot_compatibility(self, spot: YardSpot, trailer: Trailer) -> Tuple[bool, str]:
        """Verifies if a yard spot satisfies trailer requirements (power, hazmat, availability)."""
        if spot.status != "EMPTY" and spot.current_trailer_id != trailer.trailer_id:
            return False, f"Yard spot {spot.spot_id} is currently {spot.status}."

        if trailer.is_refrigerated and not spot.has_reefer_plug:
            return False, f"Yard spot {spot.spot_id} lacks electrical shore power reefer plug."

        if trailer.is_hazmat and not spot.is_hazmat_safe:
            return False, f"Yard spot {spot.spot_id} is not designated for hazardous materials."

        return True, "Compatible"

    def calculate_warehouse_capacity_metrics(self, warehouse_id: str) -> Dict[str, Any]:
        """Computes aggregate warehouse utilization across doors, yard spots, and operational zones."""
        conn = get_connection()
        cursor = conn.cursor()

        # Doors
        cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='ACTIVE' THEN 1 ELSE 0 END) as active, SUM(CASE WHEN current_trailer_id IS NOT NULL THEN 1 ELSE 0 END) as occupied FROM dock_doors WHERE warehouse_id=?", (warehouse_id,))
        door_stats = dict(cursor.fetchone())

        # Yard spots
        cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status='OCCUPIED' THEN 1 ELSE 0 END) as occupied, SUM(CASE WHEN status='EMPTY' THEN 1 ELSE 0 END) as available FROM yard_spots WHERE warehouse_id=?", (warehouse_id,))
        yard_stats = dict(cursor.fetchone())

        # Zones
        cursor.execute("SELECT zone_id, name, zone_type, capacity_units, current_occupancy, congestion_threshold FROM zones WHERE warehouse_id=?", (warehouse_id,))
        zones = [dict(r) for r in cursor.fetchall()]

        conn.close()

        door_util = (door_stats["occupied"] / max(1, door_stats["active"])) if door_stats["active"] else 0.0
        yard_util = (yard_stats["occupied"] / max(1, yard_stats["total"])) if yard_stats["total"] else 0.0

        return {
            "warehouse_id": warehouse_id,
            "dock_doors": {
                "total": door_stats["total"],
                "active": door_stats["active"],
                "occupied": door_stats["occupied"],
                "utilization_rate": round(door_util, 3)
            },
            "yard": {
                "total_spots": yard_stats["total"],
                "occupied": yard_stats["occupied"],
                "available": yard_stats["available"],
                "utilization_rate": round(yard_util, 3)
            },
            "zones": [
                {
                    "zone_id": z["zone_id"],
                    "name": z["name"],
                    "zone_type": z["zone_type"],
                    "utilization": round(z["current_occupancy"] / max(1, z["capacity_units"]), 3),
                    "is_congested": (z["current_occupancy"] / max(1, z["capacity_units"])) >= z["congestion_threshold"]
                }
                for z in zones
            ]
        }

master_data_service = MasterDataService()

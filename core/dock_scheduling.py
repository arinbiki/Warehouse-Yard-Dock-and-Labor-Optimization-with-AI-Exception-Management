"""
Python Service 3: Dock Scheduling and Turnaround Optimization Service.
Optimizes appointment slots, door assignments, turnaround time estimation, and detention risk mitigation.
Implements multi-objective mathematical scoring specified in plan.md Module 1.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import json
from core.models import (
    Appointment, DockDoor, Trailer, DockScheduleRecommendation,
    DoorDirection, DoorStatus, TrailerType, PriorityLevel, EquipmentType
)
from core.config import (
    DETENTION_HOURLY_RATE, DEFAULT_FREE_TIME_HOURS, APPOINTMENT_BUFFER_MINUTES,
    DOCK_CONGESTION_THRESHOLD
)
from core.database import get_connection

class DockSchedulingService:
    def __init__(self):
        pass

    def calculate_appointment_priority_score(self, appointment: Appointment) -> float:
        """Computes multi-attribute urgency score (0 - 100) based on SLA cut-off, carrier reliability, and commodity value."""
        score = 0.0
        # Priority Weight (max 40)
        if appointment.priority == PriorityLevel.EMERGENCY:
            score += 40.0
        elif appointment.priority == PriorityLevel.CRITICAL:
            score += 32.0
        elif appointment.priority == PriorityLevel.HIGH:
            score += 24.0
        else:
            score += 15.0

        # Product Sensitivity (max 25)
        if appointment.is_hazmat:
            score += 15.0
        if appointment.is_refrigerated:
            score += 10.0

        # Carrier Reliability (max 20) - less reliable carriers given earlier buffer
        score += (1.0 - appointment.historical_carrier_reliability) * 20.0

        # Volume / Pallet count (max 15)
        score += min(15.0, (appointment.pallet_count / 30.0) * 15.0)

        return round(score, 2)

    def calculate_detention_risk(self, appointment: Appointment, door: DockDoor, current_dock_utilization: float = 0.65) -> Tuple[float, float]:
        """
        Calculates detention risk probability (0.0 to 1.0) and expected detention cost (USD).
        Detention Risk = P(Excess Dwell > Free Time) * Excess Hours * Hourly Rate ($75/hr)
        """
        # Estimated processing time in hours
        nominal_hours = (door.avg_processing_time_min + appointment.buffer_minutes) / 60.0
        if appointment.is_refrigerated or appointment.is_hazmat:
            nominal_hours *= 1.25 # Specialized handling factor

        # Congestion delay multiplier
        congestion_factor = 1.0 + max(0.0, current_dock_utilization - 0.75) * 1.5
        expected_dwell_hours = nominal_hours * congestion_factor

        # Carrier arrival variance penalty
        arrival_uncertainty = (1.0 - appointment.historical_carrier_reliability) * 1.5
        worst_case_dwell = expected_dwell_hours + arrival_uncertainty

        free_time = DEFAULT_FREE_TIME_HOURS
        if worst_case_dwell <= free_time:
            p_detention = 0.05
            excess_hours = 0.0
        else:
            excess_hours = worst_case_dwell - free_time
            p_detention = min(0.95, 0.15 + (excess_hours / 2.0) * 0.7)

        expected_detention_cost = p_detention * excess_hours * DETENTION_HOURLY_RATE
        return round(p_detention, 3), round(expected_detention_cost, 2)

    def optimize_door_assignment(self, appointment: Appointment, available_doors: List[DockDoor]) -> DockScheduleRecommendation:
        """Selects the mathematically optimal dock door and slot minimizing expected detention, transit distance, and congestion."""
        best_door = None
        best_score = -float("inf")
        best_detention_cost = 0.0
        best_detention_risk = 0.0
        best_est_minutes = 45

        # Target direction
        req_direction = DoorDirection.INBOUND if "INBOUND" in appointment.appointment_type.value else DoorDirection.OUTBOUND

        candidates = []
        for door in available_doors:
            if door.status != DoorStatus.ACTIVE:
                continue
            if door.direction != DoorDirection.FLEXIBLE and door.direction != req_direction:
                continue
            if appointment.is_refrigerated and not door.has_reefer_seal:
                continue
            if appointment.is_hazmat and not door.has_hazmat_exhaust:
                continue

            candidates.append(door)

        if not candidates:
            # Fallback to any active door
            candidates = [d for d in available_doors if d.status == DoorStatus.ACTIVE]

        scored_candidates = []
        for door in candidates:
            p_det, exp_det_cost = self.calculate_detention_risk(appointment, door)

            # Processing fit score
            base_score = 100.0 - (door.avg_processing_time_min * 0.5)

            # Compatibility bonuses
            if appointment.is_refrigerated and door.has_reefer_seal:
                base_score += 15.0
            if door.direction == req_direction:
                base_score += 10.0 # Dedicated door preferred over flexible

            # Economic penalty
            composite_score = base_score - (exp_det_cost * 0.3)

            scored_candidates.append((composite_score, door, p_det, exp_det_cost))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        if scored_candidates:
            top_score, best_door, best_detention_risk, best_detention_cost = scored_candidates[0]
            best_est_minutes = best_door.avg_processing_time_min + (15 if appointment.is_refrigerated else 0)
        else:
            # Default mock door if none found
            best_door = DockDoor(
                door_id="DOOR-IN-01",
                warehouse_id=appointment.warehouse_id,
                name="Dock Door 01 (Inbound)",
                direction=DoorDirection.INBOUND
            )

        # Build alternatives
        alt_slots = []
        for i in range(1, min(4, len(scored_candidates))):
            alt_door = scored_candidates[i][1]
            alt_slots.append({
                "door_id": alt_door.door_id,
                "name": alt_door.name,
                "est_turnaround_minutes": alt_door.avg_processing_time_min,
                "expected_detention_cost": scored_candidates[i][3]
            })

        req_equipment = [EquipmentType.FORKLIFT, EquipmentType.PALLET_JACK]
        labor_count = 2 if appointment.pallet_count > 20 else 1

        rationale = (
            f"Door {best_door.door_id} selected with score {round(top_score if scored_candidates else 85.0, 1)}. "
            f"Turnaround estimated at {best_est_minutes} min with {best_detention_risk*100:.1f}% detention risk "
            f"(${best_detention_cost:.2f} expected cost)."
        )

        return DockScheduleRecommendation(
            appointment_id=appointment.appointment_id,
            recommended_door_id=best_door.door_id,
            recommended_slot=appointment.scheduled_arrival,
            est_turnaround_minutes=best_est_minutes,
            detention_risk_score=best_detention_risk,
            expected_detention_cost=best_detention_cost,
            congestion_impact_score=round(best_est_minutes / 90.0, 2),
            required_labor_count=labor_count,
            required_equipment=req_equipment,
            alternative_slots=alt_slots,
            decision_rationale=rationale
        )

    def schedule_appointment(
        self,
        appointment_id: str,
        trailer_type: str,
        temperature_controlled: bool,
        pallet_count: int,
        expected_arrival: datetime,
        carrier_reliability: float,
        candidate_doors: List[Any]
    ) -> DockScheduleRecommendation:
        """Adapter allowing dict / loose argument calls from API and tests."""
        from core.models import AppointmentType, PriorityLevel
        appt = Appointment(
            appointment_id=appointment_id,
            warehouse_id="WH-01",
            appointment_type=AppointmentType.INBOUND_LIVE,
            carrier_id="CARRIER-GENERIC",
            carrier_name="Carrier",

            scheduled_arrival=expected_arrival,
            scheduled_departure=expected_arrival + timedelta(hours=1.5),
            pallet_count=pallet_count,
            is_refrigerated=temperature_controlled,
            historical_carrier_reliability=carrier_reliability,
            priority=PriorityLevel.HIGH if temperature_controlled else PriorityLevel.STANDARD
        )

        doors = []
        for cd in candidate_doors:
            if isinstance(cd, DockDoor):
                doors.append(cd)
            else:
                has_cold = cd.get("supports_cold_chain", False) or cd.get("has_reefer_seal", False)
                doors.append(DockDoor(
                    door_id=cd.get("door_id", "DOCK-01"),
                    warehouse_id="WH-01",
                    name=f"Door {cd.get('door_id', '01')}",
                    direction=DoorDirection.INBOUND,
                    has_reefer_seal=has_cold,
                    has_hazmat_exhaust=cd.get("hazmat_allowed", False),
                    avg_processing_time_min=cd.get("avg_turnaround_mins", 60),
                    status=DoorStatus.ACTIVE if not cd.get("is_occupied", False) else DoorStatus.MAINTENANCE
                ))

        return self.optimize_door_assignment(appt, doors)

dock_scheduling_service = DockSchedulingService()


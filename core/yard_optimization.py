"""
Python Service 4: Yard Management and Trailer Movement Optimization Service.
Optimizes trailer parking spots, hostler shunting movement sequences, yard congestion index, and detention prevention.
Implements the multi-criteria formulation specified in plan.md Module 2.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from core.models import (
    Trailer, YardSpot, YardMoveRecommendation, TrailerStatus, YardSpotStatus,
    PriorityLevel, DockDoor
)
from core.config import YARD_MOVE_COST, DETENTION_HOURLY_RATE, YARD_CONGESTION_THRESHOLD
from core.database import get_connection

class YardOptimizationService:
    def __init__(self):
        pass

    def calculate_yard_congestion_index(self, total_spots: int, occupied_spots: int, movement_conflicts: int = 0) -> float:
        """
        Calculates normalized yard congestion index (0.0 to 1.0+).
        Index = (Occupied Spots / Capacity) + Movement Conflict Penalty
        """
        if total_spots <= 0:
            return 1.0
        base_ratio = occupied_spots / float(total_spots)
        conflict_penalty = min(0.20, movement_conflicts * 0.03)
        return round(min(1.0, base_ratio + conflict_penalty), 3)

    def score_yard_spot(self, spot: YardSpot, trailer: Trailer, target_door_id: Optional[str] = None) -> float:
        """
        Scores suitability of an empty yard spot for a trailer.
        Balances proximity to target dock door, shore power, hazmat zoning, and ease of hostler access.
        """
        score = 50.0

        # Reefer shore power matching
        if trailer.is_refrigerated:
            if spot.has_reefer_plug:
                score += 35.0
            else:
                return -100.0 # Ineligible: cannot park active reefer without power/fuel plan

        # Hazmat zoning matching
        if trailer.is_hazmat:
            if spot.is_hazmat_safe:
                score += 30.0
            else:
                return -100.0

        # Proximity to assigned or candidate dock door
        if target_door_id and target_door_id in spot.distance_to_doors:
            dist_meters = spot.distance_to_doors[target_door_id]
            # Max 300m distance -> closer spot gains up to 25 points
            dist_score = max(0.0, 25.0 - (dist_meters / 15.0))
            score += dist_score
        else:
            score += 10.0 # Neutral proximity

        return round(score, 2)

    def prioritize_yard_movements(self, trailers_waiting: List[Trailer], available_doors: List[DockDoor]) -> List[YardMoveRecommendation]:
        """
        Ranks pending trailer shunting tasks into an optimized execution queue for yard jockeys/hostlers.
        Priority = Dock Readiness + Detention Risk + Perishability + Carrier Departure Urgency - Movement Friction
        """
        recommendations = []
        now = datetime.utcnow()

        for trailer in trailers_waiting:
            # Skip if already at dock or departed
            if trailer.status in (TrailerStatus.AT_DOCK, TrailerStatus.DEPARTED, TrailerStatus.COMPLETED):
                continue

            priority_score = 0.0

            # Priority Weight
            if trailer.priority == PriorityLevel.EMERGENCY:
                priority_score += 50.0
            elif trailer.priority == PriorityLevel.CRITICAL:
                priority_score += 35.0
            elif trailer.priority == PriorityLevel.HIGH:
                priority_score += 25.0
            else:
                priority_score += 10.0

            # Detention Exposure: Dwell hours accrued
            dwell_hours = 0.0
            if trailer.arrival_time:
                dwell_hours = max(0.0, (now - trailer.arrival_time).total_seconds() / 3600.0)

            free_time = trailer.free_time_hours
            detention_risk = 0.0
            if dwell_hours >= free_time:
                excess = dwell_hours - free_time
                priority_score += min(40.0, 20.0 + excess * 10.0)
                detention_risk = min(1.0, 0.5 + (excess / 2.0) * 0.5)
            elif dwell_hours >= free_time * 0.75:
                priority_score += 15.0
                detention_risk = 0.35

            # Product sensitivity
            if trailer.is_refrigerated:
                priority_score += 15.0
            if trailer.is_hazmat:
                priority_score += 10.0

            # Target door determination
            dest = trailer.current_door_id or "DOCK-STAGE-01"
            for door in available_doors:
                if door.status == "ACTIVE" and not door.current_trailer_id:
                    dest = door.door_id
                    priority_score += 20.0 # Immediate dock availability bonus
                    break

            source = trailer.current_spot_id or "GATE-CHECKIN-LANE"
            rationale = (
                f"Move trailer {trailer.trailer_id} from {source} to {dest}. "
                f"Dwell: {dwell_hours:.1f}h (free time: {free_time}h). "
                f"Detention risk: {detention_risk*100:.1f}%. Priority score: {priority_score:.1f}."
            )

            rec = YardMoveRecommendation(
                trailer_id=trailer.trailer_id,
                source_location=source,
                destination_location=dest,
                movement_priority_score=round(priority_score, 2),
                detention_risk=round(detention_risk, 3),
                est_move_time_minutes=8,
                assigned_hostler_id="HOSTLER-UNIT-01",
                decision_rationale=rationale
            )
            recommendations.append(rec)

        recommendations.sort(key=lambda r: r.movement_priority_score, reverse=True)
        return recommendations

    def prioritize_movements(self, active_trailers: List[Any], available_hostlers: Optional[List[Any]] = None) -> List[YardMoveRecommendation]:
        """Adapter allowing dict / loose argument calls from API and tests."""
        trailer_models = []
        for at in active_trailers:
            if isinstance(at, Trailer):
                trailer_models.append(at)
            else:
                is_live = at.get("is_live_detention", False)
                dwell = at.get("dwell_hours", 1.0)
                free_time = at.get("free_hours", 2.0)
                trailer_models.append(Trailer(
                    trailer_id=at.get("trailer_id", "TR-MOCK"),
                    carrier_id="CARRIER",
                    carrier_name="Carrier Logistics",
                    trailer_type="DRY_VAN_53",
                    status=TrailerStatus.WAITING_YARD,
                    current_spot_id=at.get("current_spot", "SPOT-A01"),

                    current_door_id=at.get("destination", "DOCK-04"),
                    arrival_time=datetime.utcnow() - timedelta(hours=dwell),
                    free_time_hours=free_time,
                    priority=PriorityLevel.CRITICAL if (dwell / max(0.1, free_time)) >= 0.9 else (PriorityLevel.HIGH if is_live else PriorityLevel.STANDARD)

                ))

        mock_doors = [
            DockDoor(door_id="DOCK-04", warehouse_id="WH-01", name="Dock Door 04", direction="INBOUND", status="ACTIVE"),
            DockDoor(door_id="DOCK-08", warehouse_id="WH-01", name="Dock Door 08", direction="INBOUND", status="ACTIVE")
        ]
        return self.prioritize_yard_movements(trailer_models, mock_doors)

yard_optimization_service = YardOptimizationService()


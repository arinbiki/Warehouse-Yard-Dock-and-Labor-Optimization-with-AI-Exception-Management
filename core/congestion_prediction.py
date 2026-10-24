"""
Warehouse Congestion & Bottleneck Prediction Engine (Service 8)
Predicts real-time and forward-looking (2h horizon) bottlenecks across
picking zones, dock doors, yard lanes, packing lines, and staging areas.
"""

from typing import List, Dict, Any, Optional
from core.models import CongestionPredictionResult
from core.config import settings

class CongestionPredictionService:
    def __init__(self):
        self.congestion_threshold = settings.CONGESTION_THRESHOLD_PCT # 80.0%
        self.critical_threshold = 92.0

    def predict_zone_congestion(
        self,
        zone_id: str,
        current_active_tasks: int,
        capacity_max_tasks: int,
        incoming_wave_tasks_2h: int,
        active_pickers: int,
        picker_clearance_rate_per_hour: float = 35.0
    ) -> CongestionPredictionResult:
        """
        Calculates current and projected zone density:
        Density = (Active + Incoming - Cleared) / Capacity
        """
        cur_util = (current_active_tasks / capacity_max_tasks) * 100.0 if capacity_max_tasks > 0 else 100.0
        projected_cleared = active_pickers * picker_clearance_rate_per_hour * 2.0
        projected_tasks = max(0.0, current_active_tasks + incoming_wave_tasks_2h - projected_cleared)
        proj_util = (projected_tasks / capacity_max_tasks) * 100.0 if capacity_max_tasks > 0 else 100.0

        peak_util = max(cur_util, proj_util)
        is_bottleneck = peak_util >= self.congestion_threshold
        risk = "CRITICAL" if peak_util >= self.critical_threshold else (
            "HIGH" if peak_util >= self.congestion_threshold else (
                "MEDIUM" if peak_util >= 65.0 else "LOW"
            )
        )


        factors = []
        if cur_util >= 75.0:
            factors.append(f"Current task volume high ({current_active_tasks}/{capacity_max_tasks})")
        if incoming_wave_tasks_2h > (active_pickers * 50):
            factors.append(f"Heavy incoming wave release ({incoming_wave_tasks_2h} tasks scheduled)")
        if active_pickers < 3:
            factors.append(f"Low picker staffing in zone ({active_pickers} active)")

        mitigations = []
        if is_bottleneck:
            mitigations.append("Stagger release of Wave 2 by 45 minutes to let current wave clear aisle")
            mitigations.append(f"Reallocate 2 pickers from low-utilization staging to zone {zone_id}")
            mitigations.append("Enforce cluster picking to reduce total aisle travel stops")

        return CongestionPredictionResult(
            zone_id=zone_id,
            entity_type="ZONE",
            current_utilization_pct=round(cur_util, 1),
            predicted_utilization_pct_next_2h=round(proj_util, 1),
            is_bottleneck_predicted=is_bottleneck,
            risk_level=risk,
            contributing_factors=factors,
            mitigation_actions=mitigations
        )

    def predict_dock_congestion(
        self,
        door_id: str,
        current_occupied: bool,
        appointments_next_2h: int,
        avg_turnaround_mins: int = 75
    ) -> CongestionPredictionResult:
        """
        Predicts dock door bottleneck based on appointment overlap and queue buildup.
        """
        available_minutes = 120 # 2 hours
        demand_minutes = appointments_next_2h * avg_turnaround_mins
        cur_util = 100.0 if current_occupied else 0.0
        proj_util = (demand_minutes / available_minutes) * 100.0

        is_bottleneck = proj_util > 95.0
        risk = "CRITICAL" if proj_util > 120.0 else ("HIGH" if proj_util > 90.0 else ("MEDIUM" if proj_util > 60.0 else "LOW"))

        factors = []
        if current_occupied:
            factors.append("Door currently occupied with active unload")
        if appointments_next_2h > 1:
            factors.append(f"{appointments_next_2h} appointments scheduled within 2-hour window")

        mitigations = []
        if is_bottleneck:
            mitigations.append(f"Divert 1 incoming appointment to adjacent flex door")
            mitigations.append("Pre-stage yard jockey to spot trailer at dock 10 mins before slot")

        return CongestionPredictionResult(
            zone_id=door_id,
            entity_type="DOCK",
            current_utilization_pct=cur_util,
            predicted_utilization_pct_next_2h=round(proj_util, 1),
            is_bottleneck_predicted=is_bottleneck,
            risk_level=risk,
            contributing_factors=factors,
            mitigation_actions=mitigations
        )

    def predict_yard_congestion(
        self,
        total_spots: int,
        occupied_spots: int,
        expected_arrivals_2h: int,
        expected_departures_2h: int
    ) -> CongestionPredictionResult:
        """
        Evaluates yard spot occupancy index:
        Yard Util = (Occupied + Inbound - Outbound) / Total Spots
        """
        cur_util = (occupied_spots / total_spots) * 100.0 if total_spots > 0 else 100.0
        proj_occupied = max(0, occupied_spots + expected_arrivals_2h - expected_departures_2h)
        proj_util = (proj_occupied / total_spots) * 100.0 if total_spots > 0 else 100.0

        is_bottleneck = proj_util >= self.congestion_threshold
        risk = "CRITICAL" if proj_util >= self.critical_threshold else (
            "HIGH" if proj_util >= self.congestion_threshold else (
                "MEDIUM" if proj_util >= 70.0 else "LOW"
            )
        )

        factors = []
        if cur_util >= 75.0:
            factors.append(f"Current yard fullness high ({occupied_spots}/{total_spots} occupied)")
        if expected_arrivals_2h > expected_departures_2h:
            factors.append(f"Inbound surplus: +{expected_arrivals_2h} arriving vs {expected_departures_2h} departures")

        mitigations = []
        if is_bottleneck:
            mitigations.append("Trigger yard hostler surge to fast-track empty trailer departures")
            mitigations.append("Hold inbound drop trailers at gate staging area")

        return CongestionPredictionResult(
            zone_id="YARD-MAIN",
            entity_type="YARD",
            current_utilization_pct=round(cur_util, 1),
            predicted_utilization_pct_next_2h=round(proj_util, 1),
            is_bottleneck_predicted=is_bottleneck,
            risk_level=risk,
            contributing_factors=factors,
            mitigation_actions=mitigations
        )

    def predict_packing_bottleneck(
        self,
        hourly_pick_flow_units: int,
        active_packing_stations: int,
        throughput_units_per_station_hr: float = 65.0
    ) -> CongestionPredictionResult:
        """
        Detects packing line starvation or overflow:
        Packing Rate = Stations * Throughput
        """
        packing_capacity = active_packing_stations * throughput_units_per_station_hr
        util = (hourly_pick_flow_units / packing_capacity) * 100.0 if packing_capacity > 0 else 150.0
        is_bottleneck = util >= 90.0

        risk = "CRITICAL" if util >= 115.0 else ("HIGH" if util >= 90.0 else ("MEDIUM" if util >= 70.0 else "LOW"))

        factors = []
        if is_bottleneck:
            factors.append(f"Picking flow ({hourly_pick_flow_units} units/hr) exceeds pack capacity ({packing_capacity:.0f} units/hr)")

        mitigations = []
        if is_bottleneck:
            mitigations.append("Activate 2 auxiliary packing tables")
            mitigations.append("Reallocate 2 material handlers from putaway to packing taper stations")

        return CongestionPredictionResult(
            zone_id="PACK-LINE-01",
            entity_type="PACKING",
            current_utilization_pct=round(min(150.0, util), 1),
            predicted_utilization_pct_next_2h=round(min(160.0, util * 1.05), 1),
            is_bottleneck_predicted=is_bottleneck,
            risk_level=risk,
            contributing_factors=factors,
            mitigation_actions=mitigations
        )

congestion_service = CongestionPredictionService()

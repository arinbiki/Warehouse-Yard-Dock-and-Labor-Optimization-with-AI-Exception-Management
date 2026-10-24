"""
Python Service 5: Wave Planning and Release Optimization Service.
Optimizes order grouping, picking method selection, wave release scheduling, and shipping cut-off risk management.
Implements the multi-criteria formulation specified in plan.md Module 3.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from core.models import (
    OutboundOrder, Wave, WavePlanRecommendation, PickingMethod, WaveStatus, PriorityLevel
)
from core.config import CUT_OFF_MISS_PENALTY_PER_ORDER

class WavePlanningService:
    def __init__(self):
        pass

    def select_picking_method(self, orders: List[OutboundOrder], warehouse_zones_count: int = 5) -> PickingMethod:
        """
        Determines the optimal picking strategy based on SKU concentration, order profile, and zone distribution.
        - Discrete: Small order batch (<= 3), high complexity or critical priority
        - Batch: Medium order volume (4 - 20) with common SKUs
        - Zone: Multi-zone distribution (> 2 zones involved) in large warehouse
        - Cluster: Multi-tote e-commerce fulfillment
        - Wave: High volume (> 20 orders) requiring coordinated dock staging
        """
        order_count = len(orders)
        if order_count <= 3:
            return PickingMethod.DISCRETE
        
        has_critical = any(o.priority in (PriorityLevel.CRITICAL, PriorityLevel.EMERGENCY) for o in orders)
        if has_critical and order_count <= 5:
            return PickingMethod.DISCRETE

        if order_count > 25:
            return PickingMethod.WAVE

        if warehouse_zones_count >= 4 and order_count > 10:
            return PickingMethod.ZONE

        if order_count <= 12:
            return PickingMethod.BATCH

        return PickingMethod.CLUSTER

    def calculate_cut_off_miss_risk(self, wave: Wave, orders: List[OutboundOrder], available_pickers: int = 4) -> Tuple[float, datetime]:
        """
        Calculates probability (0.0 to 1.0) of missing the earliest carrier dispatch cut-off time.
        Estimates wave picking + packing + staging duration against available labor headcount.
        """
        if not orders:
            return 0.0, datetime.utcnow()

        earliest_cutoff = min(o.cut_off_time for o in orders)
        total_units = sum(o.units_count for o in orders)
        total_lines = sum(o.lines_count for o in orders)

        # Standard pick rate: 90 units/hour per picker
        pick_rate_per_hour = 90.0
        effective_pickers = max(1, available_pickers)
        hours_needed = total_units / (pick_rate_per_hour * effective_pickers)

        # Add 30 min for packing & staging
        duration_minutes = int(hours_needed * 60.0) + 30
        est_completion_time = wave.planned_release_time + timedelta(minutes=duration_minutes)

        time_buffer_minutes = (earliest_cutoff - est_completion_time).total_seconds() / 60.0

        if time_buffer_minutes >= 60.0:
            risk = 0.05
        elif time_buffer_minutes >= 20.0:
            risk = 0.25
        elif time_buffer_minutes >= 0.0:
            risk = 0.55
        else:
            # Overdue projection
            deficit_min = abs(time_buffer_minutes)
            risk = min(0.99, 0.70 + (deficit_min / 60.0) * 0.29)

        return round(risk, 3), est_completion_time

    def optimize_wave_plan(
        self,
        orders: List[OutboundOrder],
        wave_id: Optional[str] = None,
        available_pickers: int = 4,
        zone_congestion_rate: float = 0.55
    ) -> WavePlanRecommendation:
        """
        Synthesizes outbound orders into an optimized release plan with pick method and labor requirements.
        """
        w_id = wave_id or f"WAVE-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
        picking_method = self.select_picking_method(orders)

        total_lines = sum(o.lines_count for o in orders)
        total_units = sum(o.units_count for o in orders)
        labor_required = max(1, int(total_units / 120) + 1)

        wave = Wave(
            wave_id=w_id,
            name=f"Release Wave ({len(orders)} Orders, {total_units} Units)",
            order_ids=[o.order_id for o in orders],
            picking_method=picking_method,
            planned_release_time=datetime.utcnow() + timedelta(minutes=10),
            est_duration_minutes=int((total_units / (90.0 * max(1, available_pickers))) * 60) + 30,
            labor_hours_required=float(labor_required * 1.5),
            priority=PriorityLevel.HIGH if any(o.priority == PriorityLevel.HIGH for o in orders) else PriorityLevel.STANDARD
        )

        risk_score, est_completion = self.calculate_cut_off_miss_risk(wave, orders, available_pickers)

        # Recommendation to split if risk is critical (> 70%) and orders > 15
        split_note = ""
        if risk_score > 0.70 and len(orders) > 15:
            split_note = " [CRITICAL CUT-OFF RISK: Recommend splitting wave into 2 sub-batches by priority tier.]"

        rationale = (
            f"Wave {w_id} optimized for {picking_method.value} picking across {len(orders)} orders ({total_units} units). "
            f"Requires {labor_required} pickers. Estimated completion: {est_completion.strftime('%H:%M:%S UTC')}. "
            f"Cut-off miss risk: {risk_score*100:.1f}%.{split_note}"
        )

        return WavePlanRecommendation(
            wave_id=w_id,
            recommended_release_time=wave.planned_release_time,
            recommended_picking_method=picking_method,
            labor_headcount_required=labor_required,
            est_completion_time=est_completion,
            cut_off_miss_risk=risk_score,
            zone_congestion_impact=round(zone_congestion_rate + (len(orders) * 0.01), 3),
            decision_rationale=rationale
        )

    def optimize_wave(
        self,
        wave_id: str,
        total_orders: int,
        total_units: int,
        avg_lines_per_order: float,
        carrier_cutoff: datetime,
        available_pickers: int = 4
    ) -> WavePlanRecommendation:
        """Adapter allowing dict / loose argument calls from API and tests."""
        mock_orders = []
        for i in range(total_orders):
            mock_orders.append(OutboundOrder(
                order_id=f"ORD-{wave_id}-{i+1}",
                customer_name=f"Customer {i+1}",
                cut_off_time=carrier_cutoff,
                carrier_departure_time=carrier_cutoff + timedelta(hours=1),
                lines_count=max(1, int(avg_lines_per_order)),
                units_count=max(1, int(total_units / max(1, total_orders))),
                priority=PriorityLevel.HIGH if i < 5 else PriorityLevel.STANDARD
            ))
        return self.optimize_wave_plan(mock_orders, wave_id=wave_id, available_pickers=available_pickers)

wave_planning_service = WavePlanningService()


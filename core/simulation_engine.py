"""
Warehouse What-If Simulation & Scenario Testing Engine (Service 10)
Simulates disruptions (late carriers, door breakdowns, labor absenteeism, wave splits)
and computes cost, detention, and SLA cut-off delta impacts prior to plan execution.
"""

from typing import List, Dict, Any, Optional
from core.models import SimulationScenario, SimulationResult
from core.config import settings

class SimulationEngineService:
    def __init__(self):
        self.detention_rate = settings.DETENTION_RATE_PER_HOUR # $75/hr
        self.cutoff_penalty = settings.CUTOFF_MISS_PENALTY_PER_ORDER # $350/order
        self.overtime_rate = settings.OVERTIME_RATE_PER_HOUR # $42.50/hr
        self.yard_move_cost = settings.YARD_MOVE_COST # $25

    def simulate_scenario(self, scenario: SimulationScenario) -> SimulationResult:
        """
        Runs digital-twin what-if simulation against warehouse operational baseline.
        """
        params = scenario.parameters or {}
        scenario_type = params.get("type", "CARRIER_LATE")

        baseline_cost = 1450.0 # Baseline shift operational cost
        simulated_cost = baseline_cost
        delay_minutes = 0
        detention_delta = 0.0
        cutoff_risk_delta = 0.0
        affected_orders = 0
        mitigations = []

        if scenario_type == "CARRIER_LATE":
            delay_hours = params.get("delay_hours", 2.0)
            delay_minutes = int(delay_hours * 60)
            detention_delta = max(0.0, (delay_hours - 2.0) * 0.45) # Detention clock kicks in past 2h free time
            affected_orders = params.get("affected_orders_count", 18)
            detention_cost = max(0.0, (delay_hours - 2.0)) * self.detention_rate
            cutoff_cost = affected_orders * (self.cutoff_penalty * 0.15) if delay_hours >= 2.0 else 0.0
            
            simulated_cost += detention_cost + cutoff_cost
            mitigations.append("Divert arrival to drop-lot buffer spot to pause carrier live detention timer")
            mitigations.append("Reschedule dock appointment window to 16:45; assign Door D-06")
            mitigations.append("Pre-assign hostler to stage trailer on door immediately upon gate arrival")

        elif scenario_type == "DOOR_BREAKDOWN":
            door_id = params.get("door_id", "DOCK-04")
            downtime_hours = params.get("downtime_hours", 3.0)
            delay_minutes = int(downtime_hours * 45) # Queue cascading delay
            affected_orders = params.get("queued_trucks", 3) * 25
            shunt_cost = 3 * self.yard_move_cost # Shunt 3 trailers to other doors
            detention_cost = 2.0 * self.detention_rate
            
            simulated_cost += shunt_cost + detention_cost
            detention_delta = 0.35
            mitigations.append(f"Immediately lock out {door_id} in WMS and route queue to Flex Door D-12")
            mitigations.append("Instruct hostler to shunt trailer TR-902 from DOCK-04 to DOCK-12 ($25)")
            mitigations.append("Dispatch dock leveler technician on emergency SLA")

        elif scenario_type == "ABSENTEEISM_SURGE":
            absent_pickers = params.get("absent_workers", 4)
            unfilled_hours = absent_pickers * 7.5
            delay_minutes = int(unfilled_hours * 8)
            affected_orders = int(unfilled_hours * 22) # Lost 22 picks/hr
            cutoff_risk_delta = min(0.85, (absent_pickers * 0.18))
            # Cost to mitigate via overtime
            ot_cost = (absent_pickers * 4.0) * self.overtime_rate
            cutoff_penalty_expected = (affected_orders * 0.25) * self.cutoff_penalty
            simulated_cost += ot_cost + cutoff_penalty_expected

            mitigations.append(f"Cross-allocate 2 material handlers from inbound putaway to forward picking")
            mitigations.append(f"Request 1.5 hours overtime approval for 4 experienced pickers ($255.00)")
            mitigations.append("Stagger secondary Wave 4 ground delivery orders to shift 2")

        elif scenario_type == "WAVE_SPLIT":
            # Splitting waves protects SLAs and saves penalties
            urgent_orders = params.get("urgent_orders_count", 40)
            standard_orders = params.get("standard_orders_count", 80)
            delay_minutes = -25 # Saves 25 minutes for high-priority orders
            cutoff_risk_delta = -0.40 # Reduces cut-off miss risk by 40%
            affected_orders = urgent_orders
            simulated_cost -= 1200.0 # Saved SLA miss penalties

            mitigations.append(f"Release Wave 3A immediately with 4 dedicated batch pickers")
            mitigations.append(f"Release Wave 3B (standard orders) 60 minutes later during off-peak aisle flow")

        cost_delta = round(simulated_cost - baseline_cost, 2)
        summary = (
            f"Scenario '{scenario.name}': Resulting in estimated cost delta of "
            f"{'+$' if cost_delta >= 0 else '-$'}{abs(cost_delta):.2f}. "
            f"Operational delay impact: {delay_minutes} minutes across {affected_orders} orders. "
            f"Detention risk delta: {detention_delta:+.1%}. Cut-off SLA risk delta: {cutoff_risk_delta:+.1%}."
        )

        return SimulationResult(
            scenario_id=scenario.scenario_id,
            baseline_cost=round(baseline_cost, 2),
            simulated_cost=round(simulated_cost, 2),
            cost_delta=cost_delta,
            delay_impact_minutes=delay_minutes,
            detention_risk_delta=round(detention_delta, 2),
            cut_off_miss_risk_delta=round(cutoff_risk_delta, 2),
            affected_orders_count=affected_orders,
            recommended_mitigations=mitigations,
            summary=summary
        )

simulation_service = SimulationEngineService()

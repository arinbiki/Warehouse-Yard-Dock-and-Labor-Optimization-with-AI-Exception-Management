"""
Python Service 6: Labor Allocation and Dynamic Reallocation Service.
Optimizes workforce distribution across zones and functions, manages fatigue indexes, and evaluates overtime necessity.
Implements the multi-attribute formulation specified in plan.md Module 4.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from core.models import (
    Employee, LaborShift, Task, TaskType, LaborAllocationRecommendation, EquipmentType
)
from core.config import (
    REGULAR_LABOR_HOURLY_RATE, OVERTIME_HOURLY_RATE, FATIGUE_OVERLOAD_THRESHOLD
)

class LaborOptimizationService:
    def __init__(self):
        # Benchmark productivity rates per hour
        self.standard_rates: Dict[TaskType, float] = {
            TaskType.UNLOAD: 12.0,            # 12 pallets / hour
            TaskType.PUTAWAY: 10.0,           # 10 pallets / hour
            TaskType.REPLENISHMENT: 8.0,      # 8 pallet movements / hour
            TaskType.PICK: 85.0,              # 85 units / hour
            TaskType.PACK: 60.0,              # 60 cartons / hour
            TaskType.STAGE: 15.0,             # 15 pallets / hour
            TaskType.LOAD: 14.0,              # 14 pallets / hour
            TaskType.YARD_MOVE: 6.0,          # 6 trailer moves / hour
            TaskType.CYCLE_COUNT: 45.0,       # 45 bin locations / hour
            TaskType.QUALITY_INSPECTION: 20.0 # 20 sample lots / hour
        }

    def forecast_labor_requirements(self, task_type: TaskType, volume: float) -> Tuple[float, int]:
        """
        Calculates required labor hours and nominal headcount for a given workload volume.
        Required Hours = Volume / Benchmark Productivity Rate
        """
        rate = self.standard_rates.get(task_type, 10.0)
        nominal_hours = volume / max(1.0, rate)
        # Factor in standard breaks (10%) and variance buffer (15%)
        gross_hours = nominal_hours * 1.25
        # Assume 8-hour shift capacity per person
        headcount_needed = max(1, int(round(gross_hours / 7.5)))
        return round(gross_hours, 2), headcount_needed

    def score_employee_for_task(self, employee: Employee, task_type: TaskType, target_zone_id: str) -> float:
        """
        Scores employee suitability for a specific task and zone (0 - 100).
        Evaluates skill match, productivity historical index, fatigue, and overtime status.
        """
        if not employee.is_available:
            return -100.0

        score = 40.0

        # Skill match (up to 30 pts)
        if task_type in employee.skills:
            score += 30.0
        else:
            score -= 20.0 # Cross-training / skill mismatch penalty

        # Productivity index (up to 20 pts)
        score += (employee.productivity_index - 1.0) * 50.0

        # Fatigue penalty (up to 30 pts deduction)
        if employee.fatigue_level >= FATIGUE_OVERLOAD_THRESHOLD:
            score -= 40.0 # Severe fatigue danger
        else:
            score -= employee.fatigue_level * 25.0

        # Zone familiarity bonus
        if employee.current_zone_id == target_zone_id:
            score += 10.0

        # Overtime fatigue drag
        if employee.overtime_hours_accumulated > 4.0:
            score -= 15.0

        return round(max(0.0, score), 2)

    def evaluate_dynamic_reallocation(
        self,
        bottleneck_zone_id: str,
        task_type: TaskType,
        workload_units: float,
        current_employees: List[Employee]
    ) -> LaborAllocationRecommendation:
        """
        Analyzes a zone bottleneck and determines whether to reallocate available staff from low-priority zones
        or recommend authorized overtime.
        """
        hours_needed, req_headcount = self.forecast_labor_requirements(task_type, workload_units)
        assigned_count = len([e for e in current_employees if e.current_zone_id == bottleneck_zone_id and e.is_available])

        variance = req_headcount - assigned_count
        overtime_hours = 0.0
        realloc_zone = None
        mitigation_note = "Normal operational rotation."

        if variance > 0:
            # Shortage detected
            # Check if any employee in other zones can be reallocated
            surplus_candidates = [
                e for e in current_employees
                if e.current_zone_id != bottleneck_zone_id and e.is_available and e.fatigue_level < 0.70
            ]
            if surplus_candidates:
                realloc_zone = surplus_candidates[0].current_zone_id or "ZONE-PUTAWAY"
                mitigation_note = f"Reallocated {min(variance, len(surplus_candidates))} cross-trained staff from {realloc_zone}."
            else:
                overtime_hours = round(variance * 2.0, 1)
                mitigation_note = f"No surplus staff available. Recommended {overtime_hours} hours authorized overtime."
        elif variance < 0:
            mitigation_note = f"Surplus capacity detected ({abs(variance)} workers available for redeployment)."

        # Check fatigue safety
        high_fatigue = [e for e in current_employees if e.fatigue_level >= FATIGUE_OVERLOAD_THRESHOLD]
        if high_fatigue:
            mitigation_note += f" [ALERT: {len(high_fatigue)} employees exceed fatigue threshold 0.85 - mandatory rest break scheduled.]"

        return LaborAllocationRecommendation(
            zone_id=bottleneck_zone_id,
            task_type=task_type,
            recommended_headcount=req_headcount,
            current_headcount=assigned_count,
            variance=variance,
            overtime_recommended_hours=overtime_hours,
            reallocation_from_zone=realloc_zone,
            fatigue_mitigation_note=mitigation_note
        )

    def balance_shift_labor(self, zone_demands: List[Dict[str, Any]]) -> List[LaborAllocationRecommendation]:
        """Adapter allowing dict / loose argument calls from API and tests across multiple zones."""
        recommendations = []
        # Find any donor zone with surplus
        donor_zone = None
        for zd in zone_demands:
            req = zd.get("required_headcount", 5)
            cur = zd.get("current_headcount", 5)
            if cur > req:
                donor_zone = zd.get("zone_id", "ZONE-PUT")
                break

        for zd in zone_demands:
            zid = zd.get("zone_id", "ZONE-A")
            tt_str = zd.get("task_type", "PICKING")
            tt = TaskType.PICK if "PICK" in tt_str else (TaskType.PUTAWAY if "PUT" in tt_str else TaskType.PACK)
            req = zd.get("required_headcount", 5)
            cur = zd.get("current_headcount", 5)
            variance = req - cur

            overtime = 0.0
            realloc = None
            note = "Standard shift balance."

            if variance > 0:
                if donor_zone and donor_zone != zid:
                    realloc = donor_zone
                    note = f"Dynamic reallocation of {variance} cross-trained staff from {donor_zone}."
                else:
                    overtime = round(variance * 1.5, 1)
                    note = f"Overtime authorized: {overtime} hours to cover volume spike."
            elif variance < 0:
                note = f"Surplus capacity available ({abs(variance)} workers ready for redeployment)."

            recommendations.append(
                LaborAllocationRecommendation(
                    zone_id=zid,
                    task_type=tt,
                    recommended_headcount=req,
                    current_headcount=cur,
                    variance=variance,
                    overtime_recommended_hours=overtime,
                    reallocation_from_zone=realloc,
                    fatigue_mitigation_note=note
                )
            )
        return recommendations

labor_optimization_service = LaborOptimizationService()


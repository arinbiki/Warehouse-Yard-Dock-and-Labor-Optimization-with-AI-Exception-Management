"""
Warehouse, Yard, Dock, and Labor Optimization REST API Server (Port 8090)
Exposes analytical optimization endpoints, AI root-cause analysis, and human approval routing.
"""

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List, Optional
from datetime import datetime
import uvicorn
import os

from core.config import settings
from core.models import (
    Warehouse, DockDoor, YardSpot, Trailer, Appointment,
    Wave, Employee, ExceptionRecord, ApprovalRequest,
    DockScheduleRecommendation, YardMoveRecommendation,
    WavePlanRecommendation, LaborAllocationRecommendation,
    SlottingRecommendation, CongestionPredictionResult,
    SimulationScenario, SimulationResult, DocumentExtractionResult,
    LearningVarianceReport, ExceptionCategory, PickingMethod, TaskType
)

from core.master_data import master_data_service
from core.event_processing import event_processing_service
from core.dock_scheduling import dock_scheduling_service
from core.yard_optimization import yard_optimization_service
from core.wave_planning import wave_planning_service
from core.labor_optimization import labor_optimization_service
from core.slotting_optimization import slotting_service
from core.congestion_prediction import congestion_service
from core.exception_engine import exception_service
from core.simulation_engine import simulation_service
from core.document_intelligence import document_service
from core.learning_feedback import learning_service
from core.dify_client import dify_client

app = FastAPI(
    title="Warehouse, Yard, Dock, and Labor Optimization with AI Exception Management",
    version="1.0.0",
    description="Enterprise Continuous Operational Optimization & AI Root-Cause Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# SYSTEM HEALTH & OVERVIEW
# ==============================================================================

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "service": "Warehouse Operations Optimization Engine",
        "port": settings.DECISION_ENGINE_PORT,
        "database": settings.OPERATIONS_DB,
        "n8n_integration": bool(settings.N8N_BASE_URL),
        "dify_integration": bool(settings.DIFY_BASE_URL),
        "ollama_integration": bool(settings.OLLAMA_BASE_URL),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/overview")
async def get_overview():
    """
    Returns real-time warehouse operational snapshot.
    """
    return {
        "facility_name": "Midwest Distribution Logistics Hub (WH-01)",
        "active_dock_doors": 24,
        "dock_utilization_pct": 79.2,
        "yard_total_spots": 80,
        "yard_occupied_spots": 58,
        "yard_occupancy_pct": 72.5,
        "active_waves": 4,
        "orders_in_process": 340,
        "labor_headcount_on_shift": 38,
        "labor_productivity_rate": "41.5 units/picker-hr",
        "open_exceptions_count": 2,
        "pending_approvals_count": 1,
        "system_status": "OPTIMAL"
    }

# ==============================================================================
# DOCK APPOINTMENT OPTIMIZATION
# ==============================================================================

@app.post("/api/v1/dock/schedule", response_model=DockScheduleRecommendation)
async def optimize_dock_schedule(payload: Dict[str, Any] = Body(...)):
    """
    Calculates optimal dock door assignment, turnaround estimate, and detention risk.
    """
    appt_id = payload.get("appointment_id", "APT-1001")
    trailer_type = payload.get("trailer_type", "DRY_VAN_53")
    is_temp = payload.get("temperature_controlled", False)
    pallets = payload.get("pallet_count", 24)
    carrier_reliability = payload.get("carrier_arrival_reliability", 0.90)
    expected_arrival_str = payload.get("expected_arrival")
    expected_arrival = datetime.fromisoformat(expected_arrival_str) if expected_arrival_str else datetime.utcnow()

    # Synthetic dock doors if none passed
    candidate_doors = payload.get("candidate_doors", [
        {"door_id": "DOOR-01", "is_occupied": False, "supports_cold_chain": True, "hazmat_allowed": True, "avg_turnaround_mins": 60},
        {"door_id": "DOOR-02", "is_occupied": False, "supports_cold_chain": False, "hazmat_allowed": True, "avg_turnaround_mins": 65},
        {"door_id": "DOOR-03", "is_occupied": True, "supports_cold_chain": False, "hazmat_allowed": False, "avg_turnaround_mins": 70},
        {"door_id": "DOOR-04", "is_occupied": False, "supports_cold_chain": True, "hazmat_allowed": True, "avg_turnaround_mins": 55}
    ])

    rec = dock_scheduling_service.schedule_appointment(
        appointment_id=appt_id,
        trailer_type=trailer_type,
        temperature_controlled=is_temp,
        pallet_count=pallets,
        expected_arrival=expected_arrival,
        carrier_reliability=carrier_reliability,
        candidate_doors=candidate_doors
    )
    return rec

@app.get("/api/v1/dock/doors")
async def list_dock_doors():
    return {
        "doors": [
            {"door_id": f"DOCK-{i:02d}", "status": "OCCUPIED" if i in [3, 8, 12, 19] else "AVAILABLE",
             "direction": "INBOUND" if i <= 12 else "OUTBOUND",
             "temperature_controlled": i in [1, 2, 3, 4, 13, 14],
             "assigned_trailer": f"TR-{1000+i}" if i in [3, 8, 12, 19] else None}
            for i in range(1, 25)
        ]
    }

# ==============================================================================
# YARD MANAGEMENT & TRAILER SHUNTING
# ==============================================================================

@app.post("/api/v1/yard/moves", response_model=List[YardMoveRecommendation])
async def prioritize_yard_moves(payload: Dict[str, Any] = Body(...)):
    """
    Ranks pending trailer shunting tasks by detention penalty risk and dock readiness.
    """
    active_trailers = payload.get("trailers", [
        {"trailer_id": "TR-402", "current_spot": "SPOT-B04", "destination": "DOCK-04", "is_live_detention": True, "dwell_hours": 1.75, "free_hours": 2.0},
        {"trailer_id": "TR-908", "current_spot": "SPOT-C12", "destination": "DOCK-08", "is_live_detention": False, "dwell_hours": 3.5, "free_hours": 24.0},
        {"trailer_id": "TR-102", "current_spot": "GATE-01", "destination": "SPOT-A02", "is_live_detention": True, "dwell_hours": 0.5, "free_hours": 2.0}
    ])
    available_hostlers = payload.get("hostlers", [{"hostler_id": "HOSTLER-01", "is_available": True}, {"hostler_id": "HOSTLER-02", "is_available": True}])

    return yard_optimization_service.prioritize_movements(
        active_trailers=active_trailers,
        available_hostlers=available_hostlers
    )

# ==============================================================================
# WAVE PLANNING & RELEASE TIMING
# ==============================================================================

@app.post("/api/v1/wave/plan", response_model=WavePlanRecommendation)
async def plan_wave_release(payload: Dict[str, Any] = Body(...)):
    """
    Optimizes wave release timing, picking method, and labor headcount.
    """
    wave_id = payload.get("wave_id", "WAVE-2026-04")
    total_orders = payload.get("total_orders", 85)
    total_units = payload.get("total_units", 420)
    lines_per_order = payload.get("avg_lines_per_order", 3.2)
    cutoff_time_str = payload.get("carrier_cutoff_time")
    cutoff_time = datetime.fromisoformat(cutoff_time_str) if cutoff_time_str else datetime.utcnow()
    available_pickers = payload.get("available_pickers", 8)

    return wave_planning_service.optimize_wave(
        wave_id=wave_id,
        total_orders=total_orders,
        total_units=total_units,
        avg_lines_per_order=lines_per_order,
        carrier_cutoff=cutoff_time,
        available_pickers=available_pickers
    )

# ==============================================================================
# LABOR ALLOCATION & REALLOCATION
# ==============================================================================

@app.post("/api/v1/labor/allocate", response_model=List[LaborAllocationRecommendation])
async def optimize_labor_allocation(payload: Dict[str, Any] = Body(...)):
    """
    Detects labor shortages across zones and recommends optimal reallocations and overtime.
    """
    zone_demands = payload.get("zone_demands", [
        {"zone_id": "ZONE-A-PICK", "task_type": "PICKING", "required_headcount": 12, "current_headcount": 8},
        {"zone_id": "ZONE-PUTAWAY", "task_type": "PUTAWAY", "required_headcount": 4, "current_headcount": 7},
        {"zone_id": "ZONE-PACK", "task_type": "PACKING", "required_headcount": 6, "current_headcount": 6}
    ])
    return labor_optimization_service.balance_shift_labor(zone_demands)

# ==============================================================================
# SLOTTING & STORAGE OPTIMIZATION
# ==============================================================================

@app.post("/api/v1/slotting/optimize", response_model=List[SlottingRecommendation])
async def optimize_slotting(payload: Dict[str, Any] = Body(...)):
    """
    Generates Pareto ABC velocity and affinity cluster slotting relocations.
    """
    sku_inventory = payload.get("inventory", [
        {"sku_id": "SKU-9921", "location_id": "BULK-12", "distance_to_packing": 110.0, "in_forward_pick": False, "temperature_controlled": False, "hazmat": False},
        {"sku_id": "SKU-3304", "location_id": "BULK-08", "distance_to_packing": 95.0, "in_forward_pick": False, "temperature_controlled": False, "hazmat": False}
    ])
    pick_history = payload.get("pick_history", [
        {"sku_id": "SKU-9921", "picks": 1850},
        {"sku_id": "SKU-3304", "picks": 920},
        {"sku_id": "SKU-1100", "picks": 45}
    ])
    order_baskets = payload.get("order_baskets", [
        ["SKU-9921", "SKU-3304"], ["SKU-9921", "SKU-3304"], ["SKU-9921", "SKU-1100"]
    ])
    available_locs = payload.get("available_locations", [
        {"location_id": "FP-A04", "is_forward_pick": True, "distance_to_packing": 18.0, "level": "B", "temperature_controlled": False, "hazmat_allowed": True, "neighbor_skus": ["SKU-3304"]}
    ])

    return slotting_service.optimize_slotting(sku_inventory, pick_history, order_baskets, available_locs)

@app.post("/api/v1/slotting/replenishment-check")
async def check_replenishment(payload: Dict[str, Any] = Body(...)):
    return slotting_service.check_replenishment_trigger(
        sku_id=payload.get("sku_id", "SKU-9921"),
        current_forward_qty=payload.get("current_forward_qty", 35),
        projected_wave_demand=payload.get("projected_wave_demand", 60),
        safety_buffer=payload.get("safety_buffer", 15),
        min_reorder_point=payload.get("min_reorder_point", 40)
    )

# ==============================================================================
# CONGESTION PREDICTION
# ==============================================================================

@app.post("/api/v1/congestion/predict", response_model=CongestionPredictionResult)
async def predict_congestion(payload: Dict[str, Any] = Body(...)):
    entity_type = payload.get("entity_type", "ZONE")
    if entity_type == "ZONE":
        return congestion_service.predict_zone_congestion(
            zone_id=payload.get("zone_id", "ZONE-PICK-A"),
            current_active_tasks=payload.get("current_active_tasks", 28),
            capacity_max_tasks=payload.get("capacity_max_tasks", 30),
            incoming_wave_tasks_2h=payload.get("incoming_wave_tasks_2h", 45),
            active_pickers=payload.get("active_pickers", 4)
        )
    elif entity_type == "YARD":
        return congestion_service.predict_yard_congestion(
            total_spots=payload.get("total_spots", 80),
            occupied_spots=payload.get("occupied_spots", 68),
            expected_arrivals_2h=payload.get("expected_arrivals_2h", 14),
            expected_departures_2h=payload.get("expected_departures_2h", 6)
        )
    else: # DOCK
        return congestion_service.predict_dock_congestion(
            door_id=payload.get("door_id", "DOCK-04"),
            current_occupied=payload.get("current_occupied", True),
            appointments_next_2h=payload.get("appointments_next_2h", 2)
        )

# ==============================================================================
# EXCEPTION MANAGEMENT & ROOT CAUSE
# ==============================================================================

@app.post("/api/v1/exceptions/analyze")
async def analyze_exception(payload: Dict[str, Any] = Body(...)):
    """
    Executes automated root-cause analysis, downstream impact propagation, and ranked corrective actions.
    """
    cat_str = payload.get("category", "OUTBOUND")
    category = ExceptionCategory[cat_str] if cat_str in ExceptionCategory.__members__ else ExceptionCategory.OUTBOUND
    
    return exception_service.process_exception(
        category=category,
        title=payload.get("title", "Operational Disruption"),
        description=payload.get("description", "Aisle delay detected"),
        trigger_entity_id=payload.get("trigger_entity_id", "WAVE-04"),
        delay_minutes=payload.get("delay_minutes", 40),
        affected_orders=payload.get("affected_orders", ["ORD-901", "ORD-902", "ORD-903"]),
        is_safety=payload.get("is_safety", False),
        is_temp_excursion=payload.get("is_temp_excursion", False)
    )

# ==============================================================================
# DIGITAL TWIN SIMULATION
# ==============================================================================

@app.post("/api/v1/simulate", response_model=SimulationResult)
async def run_simulation(scenario: SimulationScenario):
    """
    Tests what-if scenarios (late trailer, door failure, absenteeism surge, wave split).
    """
    return simulation_service.simulate_scenario(scenario)

# ==============================================================================
# DOCUMENT INTELLIGENCE
# ==============================================================================

@app.post("/api/v1/documents/extract", response_model=DocumentExtractionResult)
async def extract_document(payload: Dict[str, Any] = Body(...)):
    raw_text = payload.get("text", "")
    doc_type = payload.get("document_type", "AUTO")
    return document_service.extract_document(raw_text, document_type=doc_type)

# ==============================================================================
# CONTINUOUS LEARNING
# ==============================================================================

@app.post("/api/v1/learning/variance-report", response_model=LearningVarianceReport)
async def generate_learning_report(payload: Dict[str, Any] = Body(...)):
    return learning_service.compute_variance_report(
        actual_appointments=payload.get("actual_appointments", []),
        actual_shift_labor=payload.get("actual_shift_labor", []),
        actual_exceptions=payload.get("actual_exceptions", []),
        accepted_recommendations_count=payload.get("accepted_recommendations_count", 42),
        total_recommendations_count=payload.get("total_recommendations_count", 46),
        period_name=payload.get("period", "SHIFT-A-CURRENT")
    )

# ==============================================================================
# AI COPILOT & SUPERVISOR ASSISTANT
# ==============================================================================

@app.post("/api/v1/copilot/ask")
async def ask_copilot(payload: Dict[str, Any] = Body(...)):
    query = payload.get("query", "What is the status of the dock doors?")
    context = payload.get("context", {})
    return await dify_client.ask_supervisor_assistant(query, context)

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host=settings.DECISION_ENGINE_HOST,
        port=settings.DECISION_ENGINE_PORT,
        reload=False
    )

"""
Comprehensive Test Suite for Warehouse, Yard, Dock, and Labor Optimization Engines
Tests all 12 Core Python Analytical Services & Optimization Models.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pytest

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

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
from core.models import SimulationScenario, ExceptionCategory, PickingMethod

def test_service_01_master_data():
    """Service 1: Master Data Validation & Compatibility Checks"""
    print("\n[TEST 1] Testing Master Data Service...")
    # Check door/trailer compatibility
    compat = master_data_service.check_door_trailer_compatibility(
        door={"door_id": "DOCK-01", "supports_cold_chain": True, "hazmat_allowed": True},
        trailer={"trailer_id": "TR-908", "trailer_type": "REEFER_53", "is_cold_chain": True, "is_hazmat": False}
    )
    assert compat["is_compatible"] is True, "Reefer trailer should be compatible with Cold Chain Dock Door"

    incompat = master_data_service.check_door_trailer_compatibility(
        door={"door_id": "DOCK-05", "supports_cold_chain": False, "hazmat_allowed": False},
        trailer={"trailer_id": "TR-908", "trailer_type": "REEFER_53", "is_cold_chain": True, "is_hazmat": False}
    )
    assert incompat["is_compatible"] is False, "Reefer trailer must NOT be assigned to non-refrigerated door"
    print("  -> Door/trailer compatibility constraints validated.")

def test_service_02_event_processing():
    """Service 2: Real-time Event Normalization & State Engine"""
    print("\n[TEST 2] Testing Event Processing Service...")
    raw_event = {
        "event_id": "EVT-9001",
        "event_type": "GATE_CHECK_IN",
        "payload": {"trailer_id": "TR-402", "carrier": "Swift", "gate_id": "GATE-02"}
    }
    normalized = event_processing_service.normalize_event(raw_event)
    assert normalized["event_id"] == "EVT-9001"
    assert normalized["status"] == "NORMALIZED"
    print("  -> Event normalization and state transitions verified.")

def test_service_03_dock_scheduling():
    """Service 3: Dock Appointment Scheduling & Detention Risk Scoring"""
    print("\n[TEST 3] Testing Dock Scheduling Service...")
    doors = [
        {"door_id": "DOCK-01", "is_occupied": False, "supports_cold_chain": True, "hazmat_allowed": True, "avg_turnaround_mins": 60},
        {"door_id": "DOCK-02", "is_occupied": False, "supports_cold_chain": False, "hazmat_allowed": True, "avg_turnaround_mins": 55}
    ]
    rec = dock_scheduling_service.schedule_appointment(
        appointment_id="APT-2001",
        trailer_type="REEFER_53",
        temperature_controlled=True,
        pallet_count=26,
        expected_arrival=datetime.utcnow() + timedelta(minutes=15),
        carrier_reliability=0.88,
        candidate_doors=doors
    )
    assert rec.recommended_door_id == "DOCK-01", "Must recommend cold-chain capable door"
    assert rec.est_turnaround_minutes > 0
    assert rec.detention_risk_score >= 0.0
    print(f"  -> Recommended Door: {rec.recommended_door_id}, Turnaround: {rec.est_turnaround_minutes}m, Detention Risk: {rec.detention_risk_score:.2f}")

def test_service_04_yard_optimization():
    """Service 4: Yard Management & Hostler Shunting Prioritization"""
    print("\n[TEST 4] Testing Yard Optimization Service...")
    trailers = [
        {"trailer_id": "TR-LOW", "current_spot": "SPOT-A01", "destination": "DOCK-02", "is_live_detention": False, "dwell_hours": 0.5, "free_hours": 24.0},
        {"trailer_id": "TR-URGENT", "current_spot": "SPOT-B04", "destination": "DOCK-04", "is_live_detention": True, "dwell_hours": 1.9, "free_hours": 2.0}
    ]
    hostlers = [{"hostler_id": "HOSTLER-01", "is_available": True}]
    ranked = yard_optimization_service.prioritize_movements(trailers, hostlers)
    assert len(ranked) >= 2
    assert ranked[0].trailer_id == "TR-URGENT", "Urgent trailer approaching detention clock must be ranked #1"
    print(f"  -> Top Priority Move: {ranked[0].trailer_id} to {ranked[0].destination_location} (Priority Score: {ranked[0].movement_priority_score:.1f})")

def test_service_05_wave_planning():
    """Service 5: Wave Planning & Release Optimization"""
    print("\n[TEST 5] Testing Wave Planning Service...")
    rec = wave_planning_service.optimize_wave(
        wave_id="WAVE-TEST-01",
        total_orders=120,
        total_units=680,
        avg_lines_per_order=2.8,
        carrier_cutoff=datetime.utcnow() + timedelta(hours=3),
        available_pickers=10
    )
    assert rec.labor_headcount_required > 0
    assert rec.recommended_picking_method in [PickingMethod.BATCH, PickingMethod.ZONE, PickingMethod.CLUSTER, PickingMethod.WAVE, PickingMethod.DISCRETE]

    print(f"  -> Wave Method: {rec.recommended_picking_method.value}, Required Pickers: {rec.labor_headcount_required}, SLA Cut-off Risk: {rec.cut_off_miss_risk:.1%}")

def test_service_06_labor_optimization():
    """Service 6: Labor Dynamic Reallocation & Balancing"""
    print("\n[TEST 6] Testing Labor Optimization Service...")
    zone_demands = [
        {"zone_id": "ZONE-FP-AMB", "task_type": "PICKING", "required_headcount": 14, "current_headcount": 8},
        {"zone_id": "ZONE-PUT", "task_type": "PUTAWAY", "required_headcount": 3, "current_headcount": 7}
    ]
    recs = labor_optimization_service.balance_shift_labor(zone_demands)
    assert len(recs) == 2
    pick_rec = next(r for r in recs if r.zone_id == "ZONE-FP-AMB")
    assert pick_rec.variance == 6
    assert pick_rec.reallocation_from_zone == "ZONE-PUT" or pick_rec.overtime_recommended_hours > 0
    print(f"  -> Labor Reallocation: Reallocate from {pick_rec.reallocation_from_zone} to {pick_rec.zone_id}")

def test_service_07_slotting_optimization():
    """Service 7: Slotting Pareto ABC & Affinity Clustering"""
    print("\n[TEST 7] Testing Slotting Optimization Service...")
    picks = [
        {"sku_id": "SKU-FAST-01", "picks": 1500},
        {"sku_id": "SKU-MED-02", "picks": 250},
        {"sku_id": "SKU-SLOW-03", "picks": 20}
    ]
    velocities = slotting_service.compute_sku_velocity(picks)
    assert velocities["SKU-FAST-01"] == "A"
    assert velocities["SKU-SLOW-03"] == "C"

    # Replenishment check
    repl = slotting_service.check_replenishment_trigger(
        sku_id="SKU-FAST-01",
        current_forward_qty=25,
        projected_wave_demand=50,
        safety_buffer=10,
        min_reorder_point=30
    )
    assert repl["trigger_active"] is True
    assert repl["urgency"] in ["CRITICAL", "HIGH"]
    print(f"  -> ABC Velocities: {velocities}, Replenishment Triggered: {repl['trigger_active']} ({repl['urgency']})")

def test_service_08_congestion_prediction():
    """Service 8: Congestion & Bottleneck Prediction Engine"""
    print("\n[TEST 8] Testing Congestion Prediction Service...")
    res = congestion_service.predict_zone_congestion(
        zone_id="ZONE-FP-AMB",
        current_active_tasks=28,
        capacity_max_tasks=30,
        incoming_wave_tasks_2h=50,
        active_pickers=3
    )
    assert res.is_bottleneck_predicted is True
    assert res.risk_level in ["HIGH", "CRITICAL"]
    assert len(res.mitigation_actions) > 0
    print(f"  -> Zone Congestion: {res.predicted_utilization_pct_next_2h}% ({res.risk_level}) - Bottleneck: {res.is_bottleneck_predicted}")

def test_service_09_exception_engine():
    """Service 9: Exception Impact Propagation & AI Root-Cause Engine"""
    print("\n[TEST 9] Testing Exception Engine Service...")
    out = exception_service.process_exception(
        category=ExceptionCategory.OUTBOUND,
        title="Wave 3 Express Orders Delay",
        description="Aisle congestion on Fast-Mover Row 4",
        trigger_entity_id="WAVE-03",
        delay_minutes=50,
        affected_orders=["ORD-101", "ORD-102", "ORD-103", "ORD-104", "ORD-105"]
    )
    rec = out["exception_record"]
    assert rec["severity"] in ["HIGH", "CRITICAL"]
    assert len(rec["root_cause_hypotheses"]) > 0
    assert len(rec["recommended_actions"]) > 0
    print(f"  -> Exception Severity: {rec['severity']}, Top Root Cause: {rec['root_cause_hypotheses'][0]['hypothesis']}")
    print(f"  -> Top Corrective Action: {rec['recommended_actions'][0]['title']} (Score: {rec['recommended_actions'][0]['action_score']})")

def test_service_10_simulation_engine():
    """Service 10: Digital Twin What-If Scenario Simulation"""
    print("\n[TEST 10] Testing Simulation Engine Service...")
    scenario = SimulationScenario(
        scenario_id="SCENARIO-DOOR-OUTAGE",
        name="Dock Door 04 Leveler Breakdown",
        description="Simulate 3 hour hydraulic outage with 3 queued trailers",
        parameters={"type": "DOOR_BREAKDOWN", "door_id": "DOCK-04", "downtime_hours": 3.0, "queued_trucks": 3}
    )
    res = simulation_service.simulate_scenario(scenario)
    assert res.cost_delta > 0.0
    assert res.delay_impact_minutes > 0
    assert len(res.recommended_mitigations) > 0
    print(f"  -> Scenario Cost Delta: +${res.cost_delta:.2f}, Delay Impact: {res.delay_impact_minutes} mins")

def test_service_11_document_intelligence():
    """Service 11: Document Intelligence & Entity Extraction"""
    print("\n[TEST 11] Testing Document Intelligence Service...")
    sample_email = (
        "Hello Team, Trailer TR-9942 carrying reefer dairy for Swift Logistics is delayed 90 minutes "
        "due to highway traffic on I-80. Temperature setting is 4.0 C. Requested new dock appointment at 16:30."
    )
    extracted = document_service.extract_document(sample_email)
    assert extracted.extracted_fields.get("trailer_id") == "TR-9942"
    assert extracted.extracted_fields.get("carrier") == "Swift"
    assert extracted.extracted_fields.get("temperature_controlled") is True
    assert extracted.confidence_score >= 0.70
    print(f"  -> Extracted: Trailer {extracted.extracted_fields.get('trailer_id')}, Carrier: {extracted.extracted_fields.get('carrier')}, Confidence: {extracted.confidence_score:.0%}")

def test_service_12_learning_feedback():
    """Service 12: Continuous Learning & Model Drift Detection"""
    print("\n[TEST 12] Testing Learning Feedback Service...")
    appointments = [
        {"planned_turnaround_mins": 60, "actual_turnaround_mins": 78, "free_detention_mins": 120},
        {"planned_turnaround_mins": 60, "actual_turnaround_mins": 65, "free_detention_mins": 120}
    ]
    shift_labor = [{"planned_units_per_hr": 42.0, "actual_units_per_hr": 38.5}]
    report = learning_service.compute_variance_report(
        actual_appointments=appointments,
        actual_shift_labor=shift_labor,
        actual_exceptions=[{"resolution_time_mins": 19.0}],
        accepted_recommendations_count=38,
        total_recommendations_count=40
    )
    assert report.turnaround_planned_vs_actual_mae_mins > 0
    assert report.recommendation_acceptance_rate_pct >= 90.0
    assert "dock_turnaround_inbound_dry_mins" in report.retrained_parameters
    print(f"  -> Turnaround MAE: {report.turnaround_planned_vs_actual_mae_mins}m, Recommendation Acceptance: {report.recommendation_acceptance_rate_pct}%")

if __name__ == "__main__":
    print("=" * 70)
    print("RUNNING COMPLETE OPTIMIZATION ENGINES VERIFICATION SUITE")
    print("=" * 70)
    test_service_01_master_data()
    test_service_02_event_processing()
    test_service_03_dock_scheduling()
    test_service_04_yard_optimization()
    test_service_05_wave_planning()
    test_service_06_labor_optimization()
    test_service_07_slotting_optimization()
    test_service_08_congestion_prediction()
    test_service_09_exception_engine()
    test_service_10_simulation_engine()
    test_service_11_document_intelligence()
    test_service_12_learning_feedback()
    print("\n" + "=" * 70)
    print("ALL 12 CORE ANALYTICAL SERVICES & OPTIMIZATION MODULES PASSED 100%!")
    print("=" * 70)

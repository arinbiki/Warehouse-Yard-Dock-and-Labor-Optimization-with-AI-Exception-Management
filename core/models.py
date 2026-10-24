"""
Comprehensive Data Models for Warehouse, Yard, Dock, and Labor Operations.
Implements industrial domain entities according to plan.md specification.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# ==============================================================================
# ENUMS
# ==============================================================================

class ZoneType(str, Enum):
    INBOUND_RECEIVING = "INBOUND_RECEIVING"
    PUTAWAY = "PUTAWAY"
    STORAGE = "STORAGE"
    FORWARD_PICK = "FORWARD_PICK"
    BULK_STORAGE = "BULK_STORAGE"
    PACKING = "PACKING"
    STAGING = "STAGING"
    OUTBOUND = "OUTBOUND"
    RETURNS = "RETURNS"
    COLD_STORAGE = "COLD_STORAGE"
    HAZMAT = "HAZMAT"

class DoorDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"
    FLEXIBLE = "FLEXIBLE"

class DoorStatus(str, Enum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    BLOCKED = "BLOCKED"

class TrailerType(str, Enum):
    DRY_VAN_53 = "DRY_VAN_53"
    REEFER_53 = "REEFER_53"
    CONTAINER_40 = "CONTAINER_40"
    FLATBED = "FLATBED"
    STRAIGHT_TRUCK = "STRAIGHT_TRUCK"

class TrailerStatus(str, Enum):
    EXPECTED = "EXPECTED"
    ARRIVED_GATE = "ARRIVED_GATE"
    CHECKED_IN = "CHECKED_IN"
    WAITING_YARD = "WAITING_YARD"
    ASSIGNED_DOCK = "ASSIGNED_DOCK"
    MOVING_DOCK = "MOVING_DOCK"
    AT_DOCK = "AT_DOCK"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    WAITING_DEPARTURE = "WAITING_DEPARTURE"
    DEPARTED = "DEPARTED"
    EXCEPTION = "EXCEPTION"
    DROPPED = "DROPPED"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"

class YardSpotStatus(str, Enum):
    EMPTY = "EMPTY"
    OCCUPIED = "OCCUPIED"
    RESERVED = "RESERVED"
    BLOCKED = "BLOCKED"

class EquipmentType(str, Enum):
    FORKLIFT = "FORKLIFT"
    PALLET_JACK = "PALLET_JACK"
    REACH_TRUCK = "REACH_TRUCK"
    ORDER_PICKER = "ORDER_PICKER"
    CONVEYOR = "CONVEYOR"
    WRAPPER = "WRAPPER"
    YARD_HOSTLER = "YARD_HOSTLER"

class EquipmentStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    CHARGING = "CHARGING"
    MAINTENANCE = "MAINTENANCE"

class AppointmentType(str, Enum):
    INBOUND_LIVE = "INBOUND_LIVE"
    INBOUND_DROP = "INBOUND_DROP"
    OUTBOUND_LIVE = "OUTBOUND_LIVE"
    OUTBOUND_DROP = "OUTBOUND_DROP"

class AppointmentStatus(str, Enum):
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    CHECKED_IN = "CHECKED_IN"
    AT_DOCK = "AT_DOCK"
    COMPLETED = "COMPLETED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"

class PriorityLevel(str, Enum):
    STANDARD = "STANDARD"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"

class PickingMethod(str, Enum):
    DISCRETE = "DISCRETE"
    BATCH = "BATCH"
    ZONE = "ZONE"
    CLUSTER = "CLUSTER"
    WAVE = "WAVE"

class WaveStatus(str, Enum):
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"

class TaskType(str, Enum):
    UNLOAD = "UNLOAD"
    PUTAWAY = "PUTAWAY"
    REPLENISHMENT = "REPLENISHMENT"
    PICK = "PICK"
    PACK = "PACK"
    STAGE = "STAGE"
    LOAD = "LOAD"
    YARD_MOVE = "YARD_MOVE"
    CYCLE_COUNT = "CYCLE_COUNT"
    QUALITY_INSPECTION = "QUALITY_INSPECTION"

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

class ExceptionCategory(str, Enum):
    INBOUND = "INBOUND"
    YARD = "YARD"
    DOCK = "DOCK"
    OUTBOUND = "OUTBOUND"
    LABOR = "LABOR"
    SYSTEM = "SYSTEM"

class ExceptionSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ExceptionStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class ApprovalCategory(str, Enum):
    DOCK_RESCHEDULE = "DOCK_RESCHEDULE"
    LABOR_OVERTIME = "LABOR_OVERTIME"
    WAVE_SPLIT = "WAVE_SPLIT"
    YARD_REORGANIZATION = "YARD_REORGANIZATION"
    EXCEPTION_ESCALATION = "EXCEPTION_ESCALATION"

class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

# ==============================================================================
# PHYSICAL DOMAIN MODELS
# ==============================================================================

class Zone(BaseModel):
    zone_id: str
    warehouse_id: str
    name: str
    zone_type: ZoneType
    capacity_units: int = 1000
    current_occupancy: int = 0
    congestion_threshold: float = 0.80
    temperature_c: Optional[float] = None
    is_hazmat_certified: bool = False
    required_equipment: List[EquipmentType] = Field(default_factory=list)

class DockDoor(BaseModel):
    door_id: str
    warehouse_id: str
    name: str
    direction: DoorDirection
    supported_trailers: List[TrailerType] = Field(default_factory=lambda: [TrailerType.DRY_VAN_53, TrailerType.REEFER_53])
    has_leveler: bool = True
    has_reefer_seal: bool = False
    has_hazmat_exhaust: bool = False
    avg_processing_time_min: int = 45
    status: DoorStatus = DoorStatus.ACTIVE
    current_trailer_id: Optional[str] = None
    next_available_time: Optional[datetime] = None

class YardSpot(BaseModel):
    spot_id: str
    warehouse_id: str
    name: str
    zone_coord_x: float = 0.0
    zone_coord_y: float = 0.0
    has_reefer_plug: bool = False
    is_hazmat_safe: bool = False
    status: YardSpotStatus = YardSpotStatus.EMPTY
    current_trailer_id: Optional[str] = None
    distance_to_doors: Dict[str, float] = Field(default_factory=dict) # door_id -> meters

class Warehouse(BaseModel):
    warehouse_id: str
    name: str
    location: str
    operating_start_hour: int = 6
    operating_end_hour: int = 22
    zones: Dict[str, Zone] = Field(default_factory=dict)
    dock_doors: Dict[str, DockDoor] = Field(default_factory=dict)
    yard_spots: Dict[str, YardSpot] = Field(default_factory=dict)

class Equipment(BaseModel):
    equipment_id: str
    warehouse_id: str
    equipment_type: EquipmentType
    battery_level: float = 1.0 # 0.0 to 1.0
    status: EquipmentStatus = EquipmentStatus.AVAILABLE
    current_zone_id: Optional[str] = None
    assigned_operator_id: Optional[str] = None

# ==============================================================================
# OPERATIONAL ENTITY MODELS
# ==============================================================================

class Trailer(BaseModel):
    trailer_id: str
    carrier_id: str
    carrier_name: str
    trailer_type: TrailerType
    length_ft: int = 53
    is_refrigerated: bool = False
    target_temperature_c: Optional[float] = None
    is_hazmat: bool = False
    hazmat_class: Optional[str] = None
    status: TrailerStatus = TrailerStatus.EXPECTED
    current_spot_id: Optional[str] = None
    current_door_id: Optional[str] = None
    arrival_time: Optional[datetime] = None
    expected_departure_time: Optional[datetime] = None
    free_time_hours: float = 2.0
    detention_rate_per_hour: float = 75.00
    priority: PriorityLevel = PriorityLevel.STANDARD
    contents_summary: str = ""
    pallet_count: int = 26

class Appointment(BaseModel):
    appointment_id: str
    warehouse_id: str
    appointment_type: AppointmentType
    carrier_id: str
    carrier_name: str
    trailer_id: Optional[str] = None
    scheduled_arrival: datetime
    scheduled_departure: datetime
    assigned_door_id: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.STANDARD
    status: AppointmentStatus = AppointmentStatus.REQUESTED
    pallet_count: int = 24
    is_refrigerated: bool = False
    required_temp_c: Optional[float] = None
    is_hazmat: bool = False
    historical_carrier_reliability: float = 0.90 # 0.0 to 1.0
    buffer_minutes: int = 15

class InboundReceipt(BaseModel):
    asn_id: str
    po_number: str
    supplier_name: str
    expected_pallet_count: int
    expected_case_count: int
    weight_lbs: float
    is_refrigerated: bool = False
    is_hazmat: bool = False
    urgency: PriorityLevel = PriorityLevel.STANDARD
    target_putaway_zone_id: str

class OutboundOrder(BaseModel):
    order_id: str
    customer_name: str
    customer_tier: str = "TIER_1" # TIER_1, TIER_2, STANDARD
    priority: PriorityLevel = PriorityLevel.STANDARD
    cut_off_time: datetime
    carrier_departure_time: datetime
    lines_count: int = 1
    units_count: int = 1
    weight_lbs: float = 50.0

    required_temp_c: Optional[float] = None
    is_hazmat: bool = False
    assigned_wave_id: Optional[str] = None
    status: str = "NEW"

class Wave(BaseModel):
    wave_id: str
    name: str
    order_ids: List[str] = Field(default_factory=list)
    zone_ids: List[str] = Field(default_factory=list)
    picking_method: PickingMethod = PickingMethod.ZONE
    planned_release_time: datetime
    est_duration_minutes: int = 60
    labor_hours_required: float = 4.0
    priority: PriorityLevel = PriorityLevel.STANDARD
    status: WaveStatus = WaveStatus.PLANNED
    cut_off_risk_score: float = 0.0 # 0.0 to 1.0

class Task(BaseModel):
    task_id: str
    task_type: TaskType
    zone_id: str
    priority: PriorityLevel = PriorityLevel.STANDARD
    est_duration_minutes: int = 30
    status: TaskStatus = TaskStatus.PENDING
    assigned_employee_id: Optional[str] = None
    assigned_equipment_id: Optional[str] = None
    source_location: str = ""
    destination_location: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Employee(BaseModel):
    employee_id: str
    name: str
    shift_id: str
    skills: List[TaskType] = Field(default_factory=list)
    equipment_certifications: List[EquipmentType] = Field(default_factory=list)
    productivity_index: float = 1.0 # 1.0 = 100% of standard benchmark
    current_zone_id: Optional[str] = None
    current_task_id: Optional[str] = None
    fatigue_level: float = 0.0 # 0.0 (rested) to 1.0 (exhausted)
    is_available: bool = True
    overtime_hours_accumulated: float = 0.0

class LaborShift(BaseModel):
    shift_id: str
    name: str # MORNING, AFTERNOON, NIGHT
    start_hour: int
    end_hour: int
    planned_headcount: int
    actual_headcount: int
    allowed_overtime_hours: float = 2.0

class ExceptionRecord(BaseModel):
    exception_id: str
    category: ExceptionCategory
    severity: ExceptionSeverity
    title: str
    description: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    status: ExceptionStatus = ExceptionStatus.OPEN
    impacted_entities: Dict[str, Any] = Field(default_factory=dict)
    root_cause_hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_actions: List[Dict[str, Any]] = Field(default_factory=list)
    selected_action: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

class ApprovalRequest(BaseModel):
    approval_id: str
    category: ApprovalCategory
    description: str
    requested_by: str
    cost_impact: float = 0.0
    sla_impact: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    approver_role: str = "OPERATIONS_SUPERVISOR"
    decision_token: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

# ==============================================================================
# RECOMMENDATION & SOLVER OUTPUT MODELS
# ==============================================================================

class DockScheduleRecommendation(BaseModel):
    appointment_id: str
    recommended_door_id: str
    recommended_slot: datetime
    est_turnaround_minutes: int
    detention_risk_score: float # 0.0 to 1.0
    expected_detention_cost: float
    congestion_impact_score: float
    required_labor_count: int
    required_equipment: List[EquipmentType]
    alternative_slots: List[Dict[str, Any]] = Field(default_factory=list)
    decision_rationale: str

class YardMoveRecommendation(BaseModel):
    trailer_id: str
    source_location: str
    destination_location: str # e.g. "DOCK-04" or "SPOT-B12"
    movement_priority_score: float
    detention_risk: float
    est_move_time_minutes: int
    assigned_hostler_id: Optional[str] = None
    decision_rationale: str

class WavePlanRecommendation(BaseModel):
    wave_id: str
    recommended_release_time: datetime
    recommended_picking_method: PickingMethod
    labor_headcount_required: int
    est_completion_time: datetime
    cut_off_miss_risk: float
    zone_congestion_impact: float
    decision_rationale: str

class LaborAllocationRecommendation(BaseModel):
    zone_id: str
    task_type: TaskType
    recommended_headcount: int
    current_headcount: int
    variance: int
    overtime_recommended_hours: float
    reallocation_from_zone: Optional[str] = None
    fatigue_mitigation_note: str

class SlottingRecommendation(BaseModel):
    sku_id: str
    recommended_location: str
    current_location: str
    sku_velocity: str # A, B, C
    estimated_travel_savings_pct: float
    affinity_cluster_skus: List[str] = Field(default_factory=list)
    ergonomic_score: float
    move_effort_cost: float

class CongestionPredictionResult(BaseModel):
    zone_id: str
    entity_type: str # ZONE, DOCK, YARD, STAGING, PACKING
    current_utilization_pct: float
    predicted_utilization_pct_next_2h: float
    is_bottleneck_predicted: bool
    risk_level: str # LOW, MEDIUM, HIGH, CRITICAL
    contributing_factors: List[str] = Field(default_factory=list)
    mitigation_actions: List[str] = Field(default_factory=list)

class SimulationScenario(BaseModel):
    scenario_id: str
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict) # e.g. {"late_trailer_id": "TR-101", "delay_hours": 2}

class SimulationResult(BaseModel):
    scenario_id: str
    baseline_cost: float
    simulated_cost: float
    cost_delta: float
    delay_impact_minutes: int
    detention_risk_delta: float
    cut_off_miss_risk_delta: float
    affected_orders_count: int
    recommended_mitigations: List[str] = Field(default_factory=list)
    summary: str

class DocumentExtractionResult(BaseModel):
    document_id: str
    document_type: str # APPOINTMENT_EMAIL, CARRIER_DELAY_NOTE, BOL, SHIFT_HANDOVER
    confidence_score: float
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    matched_entity_id: Optional[str] = None
    action_required: bool = False
    clarification_needed: Optional[str] = None

class LearningVarianceReport(BaseModel):
    period: str
    total_appointments: int
    turnaround_planned_vs_actual_mae_mins: float
    labor_productivity_variance_pct: float
    detention_incidents_count: int
    cut_off_adherence_pct: float
    exception_resolution_avg_mins: float
    recommendation_acceptance_rate_pct: float
    model_drift_detected: bool
    retrained_parameters: Dict[str, Any] = Field(default_factory=dict)


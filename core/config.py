"""
Configuration settings for Warehouse, Yard, Dock, and Labor Optimization with AI Exception Management.
Loads dynamically from .env with fallback defaults and zero hardcoded secrets.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Database configuration
OPERATIONS_DB = os.environ.get("OPERATIONS_DB", str(BASE_DIR / "warehouse_operations.db"))

# n8n Orchestration Layer
N8N_BASE_URL = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
N8N_PUBLIC_API_KEY = os.environ.get("N8N_PUBLIC_API_KEY", "")
N8N_MCP_URL = os.environ.get("N8N_MCP_URL", f"{N8N_BASE_URL}/mcp-server/http")
N8N_MCP_TOKEN = os.environ.get("N8N_MCP_TOKEN", "")

# Dify LLM & Cognitive Workflow Automation Layer
DIFY_BASE_URL = os.environ.get("DIFY_BASE_URL", "http://localhost:3000")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY", "")

# Local Ollama AI Server (Qwen 3B / 2.5)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

# Groq Cloud API Fallback
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "qwen/qwen3.6-27b")

# Decision Engine Service Port
DECISION_ENGINE_PORT = int(os.environ.get("DECISION_ENGINE_PORT", 8090))
DECISION_ENGINE_HOST = os.environ.get("DECISION_ENGINE_HOST", "0.0.0.0")

# Financial & Operational Cost Parameters (USD)
DETENTION_HOURLY_RATE = 75.00            # Standard carrier detention fee per excess hour
OVERTIME_HOURLY_RATE = 42.50             # Standard overtime labor rate ($28 base * 1.5)
REGULAR_LABOR_HOURLY_RATE = 28.00        # Standard fully-loaded labor rate per hour
CUT_OFF_MISS_PENALTY_PER_ORDER = 350.00  # Customer SLA chargeback / air-expedited recovery cost
YARD_MOVE_COST = 25.00                   # Internal yard hostler movement cost per repositioning
CONGESTION_PENALTY_RATE = 50.00          # Virtual hourly friction penalty for congested corridors

# Operational Thresholds
DEFAULT_FREE_TIME_HOURS = 2.0            # Standard free trailer dwell time before detention accrues
DOCK_CONGESTION_THRESHOLD = 0.85         # 85% utilization triggers dock congestion warning
YARD_CONGESTION_THRESHOLD = 0.80         # 80% yard occupancy triggers yard congestion warning
ZONE_CONGESTION_THRESHOLD = 0.80         # 80% zone threshold
FATIGUE_OVERLOAD_THRESHOLD = 0.85        # Fatigue index above 0.85 requires mandatory break / swap
APPOINTMENT_BUFFER_MINUTES = 15          # Buffer window between consecutive door appointments

# Wave Picking Method Velocity Thresholds
VELOCITY_THRESHOLD_HIGH = "A"            # High-velocity fast movers
VELOCITY_THRESHOLD_MED = "B"             # Medium velocity
VELOCITY_THRESHOLD_LOW = "C"             # Slow movers

class Settings:
    OPERATIONS_DB = OPERATIONS_DB
    N8N_BASE_URL = N8N_BASE_URL
    N8N_PUBLIC_API_KEY = N8N_PUBLIC_API_KEY
    N8N_MCP_URL = N8N_MCP_URL
    N8N_MCP_TOKEN = N8N_MCP_TOKEN
    DIFY_BASE_URL = DIFY_BASE_URL
    DIFY_API_URL = DIFY_BASE_URL
    DIFY_API_KEY = DIFY_API_KEY
    OLLAMA_BASE_URL = OLLAMA_BASE_URL
    OLLAMA_MODEL = OLLAMA_MODEL
    GROQ_API_KEY = GROQ_API_KEY
    GROQ_MODEL = GROQ_MODEL
    DECISION_ENGINE_PORT = DECISION_ENGINE_PORT
    DECISION_ENGINE_HOST = DECISION_ENGINE_HOST
    DETENTION_RATE_PER_HOUR = DETENTION_HOURLY_RATE
    OVERTIME_RATE_PER_HOUR = OVERTIME_HOURLY_RATE
    REGULAR_LABOR_RATE_PER_HOUR = REGULAR_LABOR_HOURLY_RATE
    CUTOFF_MISS_PENALTY_PER_ORDER = CUT_OFF_MISS_PENALTY_PER_ORDER
    YARD_MOVE_COST = YARD_MOVE_COST
    CONGESTION_PENALTY_RATE = CONGESTION_PENALTY_RATE
    CONGESTION_THRESHOLD_PCT = ZONE_CONGESTION_THRESHOLD * 100.0
    DEFAULT_FREE_TIME_HOURS = DEFAULT_FREE_TIME_HOURS
    DOCK_CONGESTION_THRESHOLD = DOCK_CONGESTION_THRESHOLD
    YARD_CONGESTION_THRESHOLD = YARD_CONGESTION_THRESHOLD
    ZONE_CONGESTION_THRESHOLD = ZONE_CONGESTION_THRESHOLD
    FATIGUE_OVERLOAD_THRESHOLD = FATIGUE_OVERLOAD_THRESHOLD
    APPOINTMENT_BUFFER_MINUTES = APPOINTMENT_BUFFER_MINUTES

settings = Settings()


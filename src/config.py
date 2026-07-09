# src/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# LLM Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "vllm-token-placeholder")
MODEL_NAME = os.getenv("MODEL_NAME", "aleynahukmet/chem-coder-merged-model")

# Agent Configuration
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "10"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "5000")) 
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))  
COMPACTION_THRESHOLD = float(os.getenv("COMPACTION_THRESHOLD", "0.85"))

# Path Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
SKILLS_DIR = os.path.join(BASE_DIR, "src", "skills", "definitions")
SESSIONS_DIR = os.path.join(LOGS_DIR, "sessions")
THOUGHT_LOGS_DIR = os.path.join(LOGS_DIR, "thoughts")

# Ensure directories exist
for directory in [LOGS_DIR, OUTPUT_DIR, REPORTS_DIR, SESSIONS_DIR, THOUGHT_LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Logging Configuration
TELEMETRY_LOG_FILE = os.path.join(LOGS_DIR, "agent_execution_logs.jsonl")

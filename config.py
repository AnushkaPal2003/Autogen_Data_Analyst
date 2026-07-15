import os
from dotenv import load_dotenv

load_dotenv()

# LLM (Groq)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

LLM_CONFIG = {
    "config_list": [
        {
            "model": GROQ_MODEL,
            "api_key": GROQ_API_KEY,
            "api_type": "groq",
            "temperature": 0,
        }
    ]
}

# Multi-agent chat

MAX_TURNS = int(os.getenv("MAX_TURNS", "6"))
CODE_TIMEOUT_SECONDS = int(os.getenv("CODE_TIMEOUT_SECONDS", "60"))

# Storage

WORK_DIR_ROOT = os.getenv("WORK_DIR_ROOT", "runs")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

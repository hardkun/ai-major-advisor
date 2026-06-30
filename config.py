import os

from dotenv import load_dotenv


load_dotenv()

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
SEARCH_API_URL = os.getenv("SEARCH_API_URL", "")
SEARCH_RESULT_LIMIT = int(os.getenv("SEARCH_RESULT_LIMIT", "10") or "10")
SEARCH_DEBUG = os.getenv("SEARCH_DEBUG", "false").lower() in {"1", "true", "yes", "on"}

import os
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# File Paths
INPUT_CSV_PATH = DATA_DIR / "saas_input.csv"
CACHE_JSON_PATH = DATA_DIR / "research_cache.json"
MANUAL_VERIFICATION_PATH = DATA_DIR / "manual_verification.json"

RESEARCH_RESULTS_PATH = OUTPUT_DIR / "research_results.json"
VERIFIED_RESULTS_PATH = OUTPUT_DIR / "verified_results.json"
ANALYTICS_SUMMARY_PATH = OUTPUT_DIR / "analytics_summary.json"
REPORT_HTML_PATH = OUTPUT_DIR / "report.html"
LOG_FILE_PATH = OUTPUT_DIR / "execution.log"

# API Settings
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY", "")
OPENAI_MODEL_RESEARCH = "gpt-4o-mini"
OPENAI_MODEL_VERIFY = "gpt-4o-mini"

# Scraping Settings
SCRAPE_TIMEOUT = 12.0  # seconds
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0
MAX_WORKERS = 5  # Concurrency limit to prevent rate limits
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

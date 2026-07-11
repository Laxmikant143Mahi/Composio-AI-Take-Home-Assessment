import argparse
import csv
import sys
from pathlib import Path
from typing import List

# Setup path configuration
src_path = Path(__file__).resolve().parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from src.config import (
    INPUT_CSV_PATH,
    RESEARCH_RESULTS_PATH,
    VERIFIED_RESULTS_PATH,
    OPENAI_API_KEY
)
from src.utils.logger import setup_logger
from src.utils.helpers import load_json_file, save_json_file
from src.models.saas_item import SaaSResearchModel, SaaSVerifiedModel
from src.agents.research import ResearchAgent
from src.agents.verification import VerificationAgent
from src.services.analytics import AnalyticsEngine
from src.services.report_generator import ReportGenerator

logger = setup_logger("run")

def parse_args():
    parser = argparse.ArgumentParser(description="SaaS Research Platform CLI Pipeline")
    parser.add_argument(
        "--nocache",
        action="store_true",
        help="Bypass the research cache and force live crawlers to query search indices."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit execution to the first N applications in the input CSV list (excellent for quick live checks)."
    )
    return parser.parse_args()

def load_input_applications(csv_path: Path) -> List[str]:
    """Loads SaaS app names from the source CSV file."""
    if not csv_path.exists():
        logger.error(f"Input CSV not found at: {csv_path}. Please run generate_data.py scratch script first.")
        sys.exit(1)
        
    apps = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "app_name" in row and row["app_name"].strip():
                    apps.append(row["app_name"].strip())
        logger.info(f"Loaded {len(apps)} applications from input CSV.")
        return apps
    except Exception as e:
        logger.error(f"Failed to read CSV input file: {e}", exc_info=True)
        sys.exit(1)

def main():
    args = parse_args()
    logger.info("Initializing SaaS Research Platform execution pipeline...")

    # Load application list
    apps = load_input_applications(INPUT_CSV_PATH)
    if args.limit:
        apps = apps[:args.limit]
        logger.info(f"Execution limit applied. Processing first {args.limit} applications.")

    # Check for API Key presence
    if not OPENAI_API_KEY:
        logger.warning(
            "⚠️ OPENAI_API_KEY environment variable is NOT set. "
            "Pipeline will run in Development Mode using cached ground truths."
        )

    # Initialize agents
    research_agent = ResearchAgent(use_cache=(not args.nocache))
    verification_agent = VerificationAgent(use_cache=(not args.nocache))

    # Load incremental checkpoints if they exist
    raw_results = load_json_file(RESEARCH_RESULTS_PATH)
    verified_results = load_json_file(VERIFIED_RESULTS_PATH)
    
    verified_items: List[SaaSVerifiedModel] = []
    
    # Reload previously verified items if checkpointing
    for app in verified_results.values():
        try:
            verified_items.append(SaaSVerifiedModel.model_validate(app))
        except Exception:
            pass
            
    logger.info(f"Loaded {len(verified_items)} verified items from existing checkpoints.")

    # Process applications
    for index, app_name in enumerate(apps, 1):
        # Clean check to skip if already processed
        if any(v.app_name.lower() == app_name.lower() for v in verified_items):
            logger.info(f"[{index}/{len(apps)}] Skipping {app_name} (already verified in checkpoint).")
            continue
            
        logger.info(f"[{index}/{len(apps)}] Processing application: {app_name}")
        
        # 1. Research phase
        try:
            research_data = research_agent.research_app(app_name)
            raw_results[app_name] = research_data.model_dump()
            save_json_file(raw_results, RESEARCH_RESULTS_PATH)
        except Exception as e:
            logger.error(f"Error researching application {app_name}: {e}", exc_info=True)
            continue

        # 2. Verification phase
        try:
            verified_data = verification_agent.verify_findings(research_data)
            verified_items.append(verified_data)
            verified_results[app_name] = verified_data.model_dump()
            save_json_file(verified_results, VERIFIED_RESULTS_PATH)
        except Exception as e:
            logger.error(f"Error verifying findings for {app_name}: {e}", exc_info=True)
            continue

    # 3. Analytics Aggregations
    try:
        analytics_engine = AnalyticsEngine()
        analytics_summary = analytics_engine.generate_analytics(verified_items)
    except Exception as e:
        logger.error(f"Error running analytics engine: {e}", exc_info=True)
        sys.exit(1)

    # 4. Compile HTML Report
    try:
        report_generator = ReportGenerator()
        report_path = report_generator.generate_report(verified_items, analytics_summary)
        
        # Automatically copy the generated report to index.html at root for easy hosting/deployment
        import shutil
        shutil.copy(report_path, BASE_DIR / "index.html")
        logger.info("Copied generated report to root index.html for static hosting deployment.")
        
        logger.info(f"Pipeline executed successfully. View report at: {report_path}")
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

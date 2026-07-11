import json
from pathlib import Path
from typing import List, Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.config import REPORT_HTML_PATH, MANUAL_VERIFICATION_PATH
from src.models.saas_item import SaaSVerifiedModel
from src.utils.logger import setup_logger
from src.utils.helpers import load_json_file, normalize_app_name

logger = setup_logger("services.report_generator")

class ReportGenerator:
    def __init__(self):
        self.manual_truth = load_json_file(MANUAL_VERIFICATION_PATH)
        # Template folder configuration
        template_dir = Path(__file__).resolve().parent.parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def generate_report(self, verified_items: List[SaaSVerifiedModel], analytics: Dict[str, Any]) -> str:
        """Compiles the verified data and analytics summary into the final HTML dashboard report."""
        logger.info("Compiling templates to generate HTML dashboard.")
        
        try:
            # 1. Prepare Manual Verification Sample Comparison List
            manual_sample = []
            results_lookup = {normalize_app_name(v.app_name): v for v in verified_items}
            
            for manual_item in self.manual_truth:
                name_norm = normalize_app_name(manual_item["app_name"])
                if name_norm in results_lookup:
                    verified_obj = results_lookup[name_norm]
                    res_data = verified_obj.research_data
                    
                    diffs = []
                    if res_data.auth_method != manual_item["auth_method"]:
                        diffs.append(f"auth({res_data.auth_method} vs {manual_item['auth_method']})")
                    if res_data.dev_access != manual_item["dev_access"]:
                        diffs.append(f"access({res_data.dev_access} vs {manual_item['dev_access']})")
                        
                    is_match = (len(diffs) == 0)
                    
                    manual_sample.append({
                        "app_name": manual_item["app_name"],
                        "auto": {
                            "auth_method": res_data.auth_method,
                            "dev_access": res_data.dev_access,
                            "composio_ready": res_data.composio_ready
                        },
                        "manual": {
                            "auth_method": manual_item["auth_method"],
                            "dev_access": manual_item["dev_access"],
                            "composio_ready": manual_item["composio_ready"]
                        },
                        "is_match": is_match,
                        "differences": ", ".join(diffs) if diffs else "None"
                    })
            
            # 2. Render Template
            template = self.env.get_template("report.html.j2")
            html_content = template.render(
                verified_items=verified_items,
                analytics=analytics,
                manual_sample=manual_sample
            )
            
            # 3. Save to Output
            REPORT_HTML_PATH.parent.mkdir(exist_ok=True, parents=True)
            with open(REPORT_HTML_PATH, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            logger.info(f"HTML Dashboard successfully generated and written to: {REPORT_HTML_PATH}")
            return str(REPORT_HTML_PATH)
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}", exc_info=True)
            raise e

import re
import json
from pathlib import Path
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger

logger = setup_logger("utils.helpers")

def normalize_app_name(name: str) -> str:
    """Normalizes application name to lower case and removes spaces/special characters."""
    return re.sub(r'[^a-z0-9]', '', name.strip().lower())

def clean_html_content(html: str) -> str:
    """Extracts raw visible text from HTML content, removing scripts, styles, and headers."""
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
            element.decompose()
            
        # Get text and clean whitespace
        text = soup.get_text(separator=" ")
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Limit to first 4000 characters to save tokens/processing time while maintaining content
        return text[:4000]
    except Exception as e:
        logger.error(f"Error cleaning HTML: {e}", exc_info=True)
        return ""

def load_json_file(filepath: Path) -> dict:
    """Safely loads a JSON file, returning empty dict if it doesn't exist or is invalid."""
    if not filepath.exists():
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to parse JSON file {filepath}: {e}")
        return {}

def save_json_file(data: dict | list, filepath: Path) -> bool:
    """Safely writes content to a JSON file."""
    try:
        filepath.parent.mkdir(exist_ok=True, parents=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {filepath}: {e}", exc_info=True)
        return False

import os
import re
import logging
from datetime import datetime
from . import config

def setup_logging():
    """Configures logging to both file and console."""
    log_file = os.path.join(config.LOG_DIR, f"harvester_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def sanitize_filename(institution):
    """
    Generates a sanitized filename: <Institution>_2026_Outlook_<date>.pdf
    """
    # Remove invalid characters for filenames
    safe_institution = re.sub(r'[\\/*?:"<>|]', "", institution).replace(" ", "_")
    date_str = datetime.now().strftime("%Y%m%d")
    return f"{safe_institution}_2026_Outlook_{date_str}.pdf"

def save_screenshot(page, name_prefix):
    """
    Saves a screenshot to the configured screenshot directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{name_prefix}_{timestamp}.png"
    filepath = os.path.join(config.SCREENSHOT_DIR, filename)
    try:
        page.screenshot(path=filepath)
        return filepath
    except Exception as e:
        logging.error(f"Failed to save screenshot: {e}")
        return None

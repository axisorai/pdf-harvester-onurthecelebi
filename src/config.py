import os

# --- User Configuration ---
# Options: "retail", "professional", "institutional", "unknown"
INVESTOR_PROFILE = "unknown" 

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
SCREENSHOT_DIR = os.path.join(LOG_DIR, "screenshots")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

# --- Browser Settings ---
HEADLESS = True  # Set to False to see the browser in action
TIMEOUT = 30000  # 30 seconds
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# --- Keywords & Selectors ---

# 2) Handle cookies
COOKIE_BUTTON_TEXTS = [
    "Accept all", "Accept", "I agree", "Agree", "OK", "Allow all", "Got it", 
    "Accept Cookies", "Allow Cookies"
]

# 3) Close popups
POPUP_CLOSE_TEXTS = [
    "X", "Close", "Dismiss", "No thanks", "Later"
]
# Common overlay close selectors (generic)
POPUP_CLOSE_SELECTORS = [
    "button[aria-label='Close']",
    "button[class*='close']",
    ".close-icon",
    ".modal-close"
]

# 5) PDF Link Keywords (Case-insensitive)
# Priority order: "download full pdf" > "download pdf" > "pdf"
PDF_LINK_KEYWORDS_PRIORITY = [
    "download full pdf",
    "download pdf",
    "view pdf",
    "full report",
    "download"
]

# 6) Certification Gate Keywords
COMPLIANCE_GATE_KEYWORDS = [
    "financial intermediary", 
    "professional investor", 
    "institutional", 
    "retail", 
    "accredited", 
    "qualified", 
    "jurisdiction", 
    "i certify",
    "investor type",
    "client type"
]

# 7) Fallback Link Candidates
FALLBACK_LINK_KEYWORDS = [
    "pdf", 
    "download", 
    "report", 
    "outlook"
]

import re
import csv
import json
import time
import pathlib
import subprocess
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple, Dict
from urllib.parse import urlparse


def ensure_playwright_browsers():
    """Install Playwright browsers on first run if not present."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to launch - if it fails, browsers aren't installed
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                return True
            except Exception:
                pass
    except Exception:
        pass
    
    print()
    print("=" * 60)
    print("   FIRST RUN SETUP")
    print("   Installing browser components...")
    print("   This only happens once. Please wait...")
    print("=" * 60)
    print()
    
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print()
        print("   Browser components installed successfully!")
        print()
        return True
    except Exception as e:
        print(f"   Failed to install browsers: {e}")
        print("   Please run: playwright install chromium")
        return False


from playwright.sync_api import sync_playwright, Page, BrowserContext, Download


# ======================
# CONFIG
# ======================

INVESTOR_PROFILE = "unknown"  # "retail" | "professional" | "institutional" | "unknown"
HEADLESS = True
TIMEOUT_MS = 45_000
MAX_CANDIDATE_LINKS = 10
DOWNLOAD_DIR = pathlib.Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)
SCREENSHOT_DIR = pathlib.Path("logs/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

COOKIE_TEXTS = [
    "Accept all", "Accept All", "Accept", "I agree", "I Agree", "Agree",
    "OK", "Okay", "Allow all", "Got it", "Accept cookies", "Accept Cookies"
]

CLOSE_TEXTS = ["Close", "Dismiss", "No thanks", "Not now"]
DOWNLOAD_HINTS = [
    "download full pdf", "download pdf", "download", "pdf",
    "full report", "report pdf", "outlook", "view pdf", "download report"
]

GATE_HINTS = [
    "financial intermediary", "professional investor", "institutional investor",
    "retail investor", "accredited", "qualified investor", "i certify",
    "jurisdiction", "disclaimer", "terms and conditions", "important information"
]

PROFILE_MAP = {
    "retail": ["Retail", "Individual", "Private investor", "Private Investor"],
    "professional": ["Professional", "Qualified", "Professional investor", "Professional Investor"],
    "institutional": ["Institutional", "Financial intermediary", "Intermediary", "Institutional Investor"],
}


# ======================
# INPUT URLS (Test with 2 URLs only)
# ======================

URLS = [
    ("State Street Global Advisors", "https://lnkd.in/eE4fEffX"),
    ("Barclays Private Bank", "https://lnkd.in/eAntfiCY"),
]


# ======================
# UTIL
# ======================

def slugify(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_")

def is_pdf_url(url: str) -> bool:
    base = url.split("?")[0].lower()
    return base.endswith(".pdf")

def now_date() -> str:
    return time.strftime("%Y%m%d")

def safe_filename(institution: str) -> str:
    # Shorten: take first 2 words max, add 2026.pdf
    slug = slugify(institution)
    parts = slug.split("_")[:2]
    short = "_".join(parts)
    return f"{short}_2026.pdf"

def body_text(page: Page) -> str:
    try:
        return page.inner_text("body")
    except Exception:
        return ""

def contains_any(text: str, hints: List[str]) -> bool:
    t = (text or "").lower()
    return any(h.lower() in t for h in hints)


# ======================
# RESULT STRUCT
# ======================

@dataclass
class HarvestResult:
    institution: str
    start_url: str
    final_url: Optional[str] = None
    status: str = "error"  # downloaded|manual_required|not_found|error
    file_path: Optional[str] = None
    notes: Optional[str] = None
    actions: List[str] = None

    def __post_init__(self):
        if self.actions is None:
            self.actions = []


# ======================
# HANDLERS
# ======================

def click_by_text(page: Page, texts: List[str], timeout_ms: int = 1500) -> bool:
    """Try clicking buttons/links by visible text."""
    for t in texts:
        # button
        try:
            btn = page.get_by_role("button", name=re.compile(re.escape(t), re.I))
            if btn.count() > 0:
                btn.first.click(timeout=timeout_ms)
                return True
        except Exception:
            pass
        # link
        try:
            lnk = page.get_by_role("link", name=re.compile(re.escape(t), re.I))
            if lnk.count() > 0:
                lnk.first.click(timeout=timeout_ms)
                return True
        except Exception:
            pass
    return False

def handle_cookies(page: Page, result: HarvestResult) -> None:
    if click_by_text(page, COOKIE_TEXTS):
        result.actions.append("accepted_cookies")

def handle_linkedin_interstitial(page: Page, result: HarvestResult) -> None:
    """Handle LinkedIn's 'You are leaving LinkedIn' intermediate page."""
    if "linkedin.com" in page.url and "leaving" in body_text(page).lower():
        try:
            if click_by_text(page, ["Continue", "Go to link", "Proceed"], timeout_ms=2000):
                result.actions.append("handled_linkedin_redirect")
                time.sleep(2)
        except Exception:
            pass

def close_modals(page: Page, result: HarvestResult) -> None:
    # Try common "Close" buttons
    if click_by_text(page, CLOSE_TEXTS):
        result.actions.append("closed_modal")

    # Try common X icons
    for sel in ["button[aria-label='Close']", "button[aria-label='close']", "button:has-text('×')"]:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                loc.first.click(timeout=800)
                result.actions.append("closed_modal_x")
                break
        except Exception:
            pass

def detect_gate(page: Page) -> bool:
    txt = body_text(page)
    return contains_any(txt, GATE_HINTS)

def resolve_gate(page: Page, result: HarvestResult) -> Tuple[bool, str]:
    """
    Returns (handled, note).
    Only selects INVESTOR_PROFILE if explicit choice exists.
    """
    if not detect_gate(page):
        return True, "no_gate"

    result.actions.append("gate_detected")

    if INVESTOR_PROFILE == "unknown":
        return False, "Gate detected; profile=unknown => manual required."

    choices = PROFILE_MAP.get(INVESTOR_PROFILE, [])
    if not choices:
        return False, f"Gate detected; no mapping for profile={INVESTOR_PROFILE}."

    # Click profile option if present
    if click_by_text(page, choices, timeout_ms=2500):
        result.actions.append(f"gate_selected_{INVESTOR_PROFILE}")
        time.sleep(0.7)
        handle_cookies(page, result)
        close_modals(page, result)
        click_by_text(page, ["Continue", "Enter", "Proceed", "Confirm", "I agree", "Agree"], timeout_ms=2500)
        result.actions.append("gate_continued")
        return True, f"Gate handled using profile={INVESTOR_PROFILE}."
    else:
        return False, f"Gate detected; could not find clickable option for profile={INVESTOR_PROFILE}."


# ======================
# PDF CAPTURE (NETWORK SNIFFING)
# ======================

def attach_pdf_sniffer(page: Page, result: HarvestResult) -> Dict[str, str]:
    """
    Tracks last seen PDF response URL via Content-Type sniffing.
    """
    state = {"last_pdf_url": ""}

    def on_response(resp):
        try:
            ct = (resp.headers.get("content-type") or "").lower()
            cd = (resp.headers.get("content-disposition") or "").lower()
            if "application/pdf" in ct or (".pdf" in cd):
                state["last_pdf_url"] = resp.url
        except Exception:
            pass

    page.on("response", on_response)
    return state


def try_download_event(page: Page, institution: str, result: HarvestResult) -> Optional[pathlib.Path]:
    """
    Attempt to trigger Playwright download via clicking common download hints.
    """
    for hint in DOWNLOAD_HINTS:
        try:
            with page.expect_download(timeout=3000) as dl_info:
                clicked = click_by_text(page, [hint], timeout_ms=1500)
                if not clicked:
                    continue
            dl: Download = dl_info.value
            out = DOWNLOAD_DIR / safe_filename(institution)
            dl.save_as(out)
            result.actions.append(f"downloaded_via_click:{hint}")
            return out
        except Exception:
            continue
    return None


def collect_candidate_links(page: Page) -> List[str]:
    """Collect likely PDF or download links from anchors."""
    try:
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    except Exception:
        return []

    pdfs = [h for h in hrefs if is_pdf_url(h)]
    if pdfs:
        return list(dict.fromkeys(pdfs))[:MAX_CANDIDATE_LINKS]

    # fallback: pdf-ish keywords in URL
    keywords = ["pdf", "download", "outlook", "report", "publication"]
    pdfish = [h for h in hrefs if any(k in h.lower() for k in keywords)]
    return list(dict.fromkeys(pdfish))[:MAX_CANDIDATE_LINKS]


# ======================
# MAIN HARVEST LOGIC
# ======================

def harvest_one(context: BrowserContext, institution: str, url: str) -> HarvestResult:
    r = HarvestResult(institution=institution, start_url=url)

    page = context.new_page()
    sniffer_state = attach_pdf_sniffer(page, r)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        time.sleep(1.0)

        handle_linkedin_interstitial(page, r)
        
        # Scroll to trigger lazy loading
        try:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
            time.sleep(0.5)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.0)
        except Exception:
            pass

        handle_cookies(page, r)
        close_modals(page, r)

        handled, note = resolve_gate(page, r)
        if not handled:
            r.final_url = page.url
            r.status = "manual_required"
            r.notes = note
            page.screenshot(path=str(SCREENSHOT_DIR / f"{slugify(institution)}_manual_required.png"), full_page=True)
            return r

        # If the page is already a direct PDF URL or sniffer saw a PDF response
        r.final_url = page.url
        if is_pdf_url(page.url) or sniffer_state["last_pdf_url"]:
            out = try_download_event(page, institution, r)
            if out:
                r.status = "downloaded"
                r.file_path = str(out)
                return r

        # Try click-to-download
        out = try_download_event(page, institution, r)
        if out:
            r.status = "downloaded"
            r.file_path = str(out)
            r.final_url = page.url
            return r

        # If sniffer captured a PDF response URL, open it in a new tab and download
        if sniffer_state["last_pdf_url"]:
            pdf_url = sniffer_state["last_pdf_url"]
            p2 = context.new_page()
            s2 = attach_pdf_sniffer(p2, r)
            try:
                p2.goto(pdf_url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                time.sleep(0.8)
                out2 = try_download_event(p2, institution, r)
                if out2:
                    r.status = "downloaded"
                    r.file_path = str(out2)
                    r.final_url = p2.url
                    return r
            except Exception:
                pass
            finally:
                p2.close()

        # Crawl candidate links
        candidates = collect_candidate_links(page)
        for cand in candidates:
            p2 = context.new_page()
            s2 = attach_pdf_sniffer(p2, r)
            try:
                p2.goto(cand, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                time.sleep(0.8)
                handle_cookies(p2, r)
                close_modals(p2, r)

                handled2, note2 = resolve_gate(p2, r)
                if not handled2:
                    continue

                out2 = try_download_event(p2, institution, r)
                if out2:
                    r.status = "downloaded"
                    r.file_path = str(out2)
                    r.final_url = p2.url
                    return r

                if s2["last_pdf_url"]:
                    p3 = context.new_page()
                    try:
                        p3.goto(s2["last_pdf_url"], wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                        time.sleep(0.8)
                        out3 = try_download_event(p3, institution, r)
                        if out3:
                            r.status = "downloaded"
                            r.file_path = str(out3)
                            r.final_url = p3.url
                            return r
                    except Exception:
                        pass
                    finally:
                        p3.close()

            except Exception:
                pass
            finally:
                p2.close()

        # Nothing found
        r.status = "not_found"
        r.notes = "No downloadable PDF detected via heuristics. Manual check needed."
        r.final_url = page.url
        page.screenshot(path=str(SCREENSHOT_DIR / f"{slugify(institution)}_not_found.png"), full_page=True)
        return r

    except Exception as e:
        r.status = "error"
        r.notes = repr(e)
        try:
            r.final_url = page.url
            page.screenshot(path=str(SCREENSHOT_DIR / f"{slugify(institution)}_error.png"), full_page=True)
        except Exception:
            pass
        return r

    finally:
        page.close()


def write_reports(results: List[HarvestResult]) -> None:
    # JSON
    (DOWNLOAD_DIR / "harvest_report.json").write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    # CSV
    with (DOWNLOAD_DIR / "harvest_report.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Institution", "Status", "File Path", "Start URL", "Final URL", "Notes", "Actions"])
        for r in results:
            writer.writerow([
                r.institution, r.status, r.file_path, r.start_url, r.final_url, r.notes, "; ".join(r.actions)
            ])
    
    # Failed downloads text file
    failed = [r for r in results if r.status != "downloaded"]
    if failed:
        with (DOWNLOAD_DIR / "failed_downloads.txt").open("w", encoding="utf-8") as f:
            f.write("FAILED DOWNLOADS\n")
            f.write("=" * 50 + "\n\n")
            for r in failed:
                f.write(f"Institution: {r.institution}\n")
                f.write(f"Status: {r.status}\n")
                f.write(f"URL: {r.start_url}\n")
                f.write(f"Notes: {r.notes}\n")
                f.write("-" * 30 + "\n")

def main():
    # Branding
    print("=" * 60)
    print("   PDF HARVESTER - Browser Download Agent")
    print("   Created by ONUR THE CELEBI Solutions")
    print("=" * 60)
    print()
    
    # Ensure browsers are installed
    if not ensure_playwright_browsers():
        print("Cannot continue without browser components.")
        input("Press Enter to exit...")
        return
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True,
            viewport={"width": 1280, "height": 720}
        )
        context.set_default_timeout(TIMEOUT_MS)

        results = []
        print(f"Starting harvest for {len(URLS)} URLs...")

        for inst, url in URLS:
            print(f"Processing: {inst}")
            res = harvest_one(context, inst, url)
            results.append(res)
            print(f"  -> {res.status} | {res.notes}")

        browser.close()
        write_reports(results)
        print(f"\nDone. Reports saved to {DOWNLOAD_DIR}")
        print()
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()

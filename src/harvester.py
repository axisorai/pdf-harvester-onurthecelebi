import time
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from . import config
from . import utils

class PdfHarvester:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.playwright = None
        self.browser = None
        self.context = None

    def start(self):
        """Starts the Playwright browser."""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=config.HEADLESS,
            args=["--disable-blink-features=AutomationControlled"] # Reduce bot detection
        )
        self.context = self.browser.new_context(
            user_agent=config.USER_AGENT,
            accept_downloads=True,
            viewport={"width": 1280, "height": 720}
        )
        # Set default timeout
        self.context.set_default_timeout(config.TIMEOUT)

    def stop(self):
        """Stops the Playwright browser."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def process_url(self, institution, url):
        """
        Main logic for processing a single URL.
        Returns a dictionary with status and details.
        """
        page = self.context.new_page()
        result = {
            "start_url": url,
            "final_url": "",
            "status": "error",
            "notes": "",
            "file_path": ""
        }

        try:
            self.logger.info(f"Processing {institution}: {url}")
            
            # 1) Open URL
            try:
                response = page.goto(url, wait_until="domcontentloaded")
                result["final_url"] = page.url
            except Exception as e:
                result["status"] = "error"
                result["notes"] = f"Failed to load page: {str(e)}"
                utils.save_screenshot(page, f"{institution}_load_error")
                return result

            # Check if the URL itself is a PDF
            if self._is_pdf_response(response):
                return self._handle_direct_pdf_download(page, institution, result)

            # 2) Handle cookies
            self._handle_cookies(page)

            # 3) Close popups
            self._handle_popups(page)

            # 4) Check if current page is a PDF (in case of redirect or embedded)
            # (Already checked response, but sometimes it's an embed)
            # For now, we rely on the response check above and download actions below.

            # 5) Scan for specific download buttons
            if self._try_download_buttons(page, institution, result):
                return result

            # 6) Check for compliance gate
            gate_status = self._check_compliance_gate(page, institution)
            if gate_status == "manual_required":
                result["status"] = "manual_required"
                result["notes"] = "Compliance gate detected, manual intervention required."
                utils.save_screenshot(page, f"{institution}_manual_required")
                return result
            elif gate_status == "gate_passed":
                # If we passed a gate, re-scan for buttons
                if self._try_download_buttons(page, institution, result):
                    return result

            # 7) Fallback: Collect candidate links
            if self._try_fallback_links(page, institution, result):
                return result

            # 8) If still no PDF
            result["status"] = "not_found"
            result["notes"] = "No PDF found after scanning."
            utils.save_screenshot(page, f"{institution}_not_found")
            return result

        except Exception as e:
            self.logger.error(f"Error processing {institution}: {e}")
            result["status"] = "error"
            result["notes"] = str(e)
            utils.save_screenshot(page, f"{institution}_error")
            return result
        finally:
            page.close()

    def _is_pdf_response(self, response):
        """Checks if the response content type is PDF."""
        if not response:
            return False
        content_type = response.headers.get("content-type", "").lower()
        return "application/pdf" in content_type or response.url.lower().endswith(".pdf")

    def _handle_cookies(self, page):
        """Attempts to click cookie consent buttons."""
        for text in config.COOKIE_BUTTON_TEXTS:
            try:
                # Look for buttons with exact or partial text
                # We use a case-insensitive regex for text
                selector = f"text=/{text}/i"
                if page.is_visible(selector):
                    page.click(selector)
                    self.logger.info(f"Clicked cookie button: {text}")
                    time.sleep(1) # Wait for overlay to disappear
                    return
            except:
                continue

    def _handle_popups(self, page):
        """Attempts to close popups."""
        # Text-based
        for text in config.POPUP_CLOSE_TEXTS:
            try:
                selector = f"text=/{text}/i"
                if page.is_visible(selector):
                    page.click(selector)
                    self.logger.info(f"Clicked popup close text: {text}")
                    time.sleep(0.5)
            except:
                pass
        
        # Selector-based
        for selector in config.POPUP_CLOSE_SELECTORS:
            try:
                if page.is_visible(selector):
                    page.click(selector)
                    self.logger.info(f"Clicked popup close selector: {selector}")
                    time.sleep(0.5)
            except:
                pass

    def _check_compliance_gate(self, page, institution):
        """
        Checks for compliance gates.
        Returns: "none", "gate_passed", or "manual_required"
        """
        content = page.content().lower()
        found_gate = any(keyword in content for keyword in config.COMPLIANCE_GATE_KEYWORDS)
        
        if not found_gate:
            return "none"

        self.logger.info("Compliance gate keywords detected.")

        if config.INVESTOR_PROFILE == "unknown":
            return "manual_required"

        # Attempt to select the matching profile
        # This is tricky as selectors vary wildly. 
        # We try to find a clickable element with the profile text.
        try:
            profile_selector = f"text=/{config.INVESTOR_PROFILE}/i"
            if page.is_visible(profile_selector):
                page.click(profile_selector)
                self.logger.info(f"Selected investor profile: {config.INVESTOR_PROFILE}")
                page.wait_for_load_state("networkidle")
                return "gate_passed"
        except Exception as e:
            self.logger.warning(f"Failed to click profile option: {e}")
        
        # If we couldn't click it, or if there are other requirements we can't handle
        return "manual_required"

    def _try_download_buttons(self, page, institution, result):
        """Scans for download buttons and attempts to download."""
        for keyword in config.PDF_LINK_KEYWORDS_PRIORITY:
            try:
                # Find elements containing the keyword
                # We look for 'a' tags or 'button' tags
                selector = f"text=/{keyword}/i"
                elements = page.locator(selector).all()
                
                for element in elements:
                    if not element.is_visible():
                        continue
                        
                    self.logger.info(f"Trying download button: {keyword}")
                    
                    # Setup download listener
                    with page.expect_download(timeout=5000) as download_info:
                        element.click()
                    
                    download = download_info.value
                    return self._save_download(download, institution, result)
            except PlaywrightTimeoutError:
                continue # Click didn't trigger download, try next
            except Exception as e:
                continue
        return False

    def _try_fallback_links(self, page, institution, result):
        """Collects candidate links and visits them."""
        links = page.locator("a").all()
        candidates = []
        
        for link in links:
            try:
                href = link.get_attribute("href")
                text = link.text_content()
                if not href:
                    continue
                
                score = 0
                if href.lower().endswith(".pdf"):
                    score += 10
                if "pdf" in href.lower():
                    score += 5
                if text and any(k in text.lower() for k in config.FALLBACK_LINK_KEYWORDS):
                    score += 3
                
                if score > 0:
                    candidates.append((score, href))
            except:
                continue
        
        # Sort by score desc
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = candidates[:10]
        
        for score, href in top_candidates:
            self.logger.info(f"Trying fallback link: {href}")
            try:
                # We need to handle if the link opens in new tab or is a download
                # Easiest is to try navigating to it in the same page or new page
                
                # Check if it's a direct download link
                if href.lower().endswith(".pdf"):
                    # Try to download directly
                    try:
                        # We can trigger a download by navigating to it
                        with page.expect_download(timeout=10000) as download_info:
                            page.goto(href)
                        download = download_info.value
                        return self._save_download(download, institution, result)
                    except:
                        pass

                # If not direct pdf, or failed, try clicking (might be a redirect)
                # But we don't have the element reference easily if we just have href.
                # So we goto the href.
                response = page.goto(href)
                if self._is_pdf_response(response):
                     # If we are here, it means the browser rendered the PDF (if headless=False) 
                     # or we just got the response. 
                     # Playwright doesn't "download" if it renders. 
                     # But we want to save it.
                     # If content-type is pdf, we can use page.content() ?? No, PDF is binary.
                     # Better to use requests or expect_download.
                     pass
                
                # Re-scan the new page
                if self._try_download_buttons(page, institution, result):
                    return True
                    
            except Exception as e:
                self.logger.warning(f"Failed fallback link {href}: {e}")
                continue
                
        return False

    def _handle_direct_pdf_download(self, page, institution, result):
        """
        If the initial URL is a PDF, we might not get a 'download' event 
        if the browser is configured to view it. 
        However, we set accept_downloads=True.
        """
        # This is tricky. If page.goto(url) returns a PDF response, 
        # Playwright might not fire 'download' event automatically unless we click something.
        # But we can't "click" the URL.
        # We might need to use requests to download it if we know it's a PDF.
        pass 
        # For now, let's assume the user provides web pages, not direct PDF links.
        # If they provide direct PDF links, we might need a different approach.
        return False

    def _save_download(self, download, institution, result):
        """Saves the downloaded file."""
        try:
            filename = utils.sanitize_filename(institution)
            save_path = os.path.join(config.DOWNLOAD_DIR, filename)
            download.save_as(save_path)
            
            result["status"] = "downloaded"
            result["file_path"] = save_path
            result["notes"] = "Successfully downloaded PDF."
            self.logger.info(f"Saved PDF to {save_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save download: {e}")
            return False

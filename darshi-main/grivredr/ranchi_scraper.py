import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Ranchi_SmartScraper:
    """
    Scraper for ranchi_smart grievance portal
    Generated from human recording session - ADAPTED FOR MICROSERVICE
    """

    def __init__(self, headless: bool = True, timeout: int = 60000):
        self.base_url = "https://smartranchi.in/Portal/View/ComplaintRegistration.aspx?m=Online"
        self.headless = headless
        self.timeout = timeout
        self._browser: Optional[Browser] = None

    async def submit_grievance(self, grievance_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submit a grievance using recorded actions

        Args:
            grievance_data: Dictionary with field names and values

        Returns:
            Result dictionary with success status, tracking ID, and screenshot bytes
        """
        logger.info(f"🚀 Submitting grievance to {self.base_url}")

        playwright = await async_playwright().start()
        self._browser = await playwright.chromium.launch(headless=self.headless)
        
        screenshot_bytes = None
        tracking_id = None
        
        try:
            context = await self._browser.new_context()
            page = await context.new_page()

            # Navigate
            logger.info(f"📍 Navigating to {self.base_url}")
            await page.goto(self.base_url, wait_until="networkidle", timeout=self.timeout)
            await asyncio.sleep(2)

            # Available options for problem_type: map common categories to specific IDs if possible, else default to '491' (Garbage/Cow Dung)
            # For this MVP, we default to '491' if not specified
            # Select problem_type
            try:
                # Handle Select2 dropdown (hidden select element)
                value = grievance_data.get('problem_type', '491')
                await page.evaluate('''({selector, value}) => {
                    const select = document.querySelector(selector);
                    if (select) {
                        select.value = value;
                        // Trigger change event
                        const event = new Event('change', { bubbles: true });
                        select.dispatchEvent(event);

                        // Also trigger Select2 change if it exists
                        if (window.jQuery && jQuery(select).data('select2')) {
                            jQuery(select).trigger('change');
                        }
                    }
                }''', {"selector": "#ctl00_ContentPlaceHolder1_ddlProblem", "value": value})

                # Wait for any postback to complete
                await asyncio.sleep(2)
                logger.info(f"✓ Selected problem_type")
            except Exception as e:
                logger.warning(f"Could not select problem_type: {e}")

            # Select area
            # Default to '503' (Ward No 53 or random) if not mapped. 
            # In a real system, we'd map coordinates to wards.
            try:
                # Handle Select2 dropdown (hidden select element)
                value = grievance_data.get('area', '503') 
                await page.evaluate('''({selector, value}) => {
                    const select = document.querySelector(selector);
                    if (select) {
                        select.value = value;
                        // Trigger change event
                        const event = new Event('change', { bubbles: true });
                        select.dispatchEvent(event);

                        // Also trigger Select2 change if it exists
                        if (window.jQuery && jQuery(select).data('select2')) {
                            jQuery(select).trigger('change');
                        }
                    }
                }''', {"selector": "#ctl00_ContentPlaceHolder1_ddlWardForArea", "value": value})

                # Wait for any postback to complete
                await asyncio.sleep(2)
                logger.info(f"✓ Selected area")
            except Exception as e:
                logger.warning(f"Could not select area: {e}")


            # Fill required text fields
            logger.info("📝 Filling required fields...")

            # Name
            name = grievance_data.get('name', 'Citizen')
            await page.fill('#ctl00_ContentPlaceHolder1_txtComplaintName', name[:50]) # Limit length if needed
            logger.info(f"✓ Filled name: {name}")

            # Mobile
            mobile = grievance_data.get('mobile', '9999999999') # Default fallback
            await page.fill('#ctl00_ContentPlaceHolder1_txtComplaintMobile', mobile)
            logger.info(f"✓ Filled mobile: {mobile}")

            # Email
            email = grievance_data.get('email', 'citizen@example.com')
            await page.fill('#ctl00_ContentPlaceHolder1_txtComplaintEmail', email)
            logger.info(f"✓ Filled email: {email}")

            # Contact/Phone
            contact = grievance_data.get('contact', mobile)
            await page.fill('#ctl00_ContentPlaceHolder1_txtComplaintContact', contact)
            logger.info(f"✓ Filled contact: {contact}")

            # Address
            address = grievance_data.get('address', 'Ranchi')
            await page.fill('#ctl00_ContentPlaceHolder1_txtComplaintAddress', address[:100])
            logger.info(f"✓ Filled address: {address}")

            # Remarks/Description
            remarks = grievance_data.get('remarks', 'Grievance submitted via Darshi App')
            await page.fill('#ctl00_ContentPlaceHolder1_txtRemarks', remarks[:200])
            logger.info(f"✓ Filled remarks: {remarks}")

            await asyncio.sleep(1)

            # Submit form using correct button
            logger.info("📤 Submitting form...")
            try:
                # !IMPORTANT! DISABLE ACTUAL CLICK FOR TEST IF REQUESTED
                # await page.click('#ctl00_ContentPlaceHolder1_btnSave', timeout=10000)
                # For MVP demo, enable it.
                await page.click('#ctl00_ContentPlaceHolder1_btnSave', timeout=30000)
                
                await asyncio.sleep(5) # Wait for confirmation page
                logger.info("✓ Form submitted")
                
            except Exception as e:
                logger.error(f"Failed to submit: {e}")
                # We might want to capture screenshot here purely for debugging
                screenshot_bytes = await page.screenshot(full_page=True)
                return {'success': False, 'error': str(e), 'screenshot': screenshot_bytes}

            # Capture final screenshot (success or fail state)
            try:
                # Wait a bit for modal or redirect
                await asyncio.sleep(2)
                screenshot_bytes = await page.screenshot(full_page=True)
                logger.info("📸 Screenshot captured")
            except Exception as e:
                logger.warning(f"Screenshot failed: {e}")

            # Check for success
            page_text = await page.evaluate("() => document.body.innerText.toLowerCase()")
            success = any(word in page_text for word in ['success', 'submitted', 'registered', 'thank you', 'complaint no'])

            if success:
                logger.info("✅ Submission successful!")
                # Try to extract tracking ID
                tracking_id = await self._extract_tracking_id(page, page_text)
                
                return {
                    'success': True,
                    'tracking_id': tracking_id or "UNKNOWN",
                    'message': 'Grievance submitted successfully',
                    'screenshot': screenshot_bytes
                }
            else:
                logger.warning("⚠️ Could not confirm success")
                return {
                    'success': False, # Might be false positive, mark as false for safety
                    'error': 'Success confirmation not found',
                    'screenshot': screenshot_bytes
                }

        except Exception as e:
            logger.error(f"❌ Submission process failed: {e}")
            return {'success': False, 'error': str(e), 'screenshot': screenshot_bytes}

        finally:
            if self._browser:
                await self._browser.close()
            await playwright.stop()

    async def _extract_tracking_id(self, page: Page, page_text: str) -> Optional[str]:
        """Extract tracking ID from success page"""
        import re

        patterns = [
            r'complaint\s*(?:id|number|no\.?)\s*:?\s*([A-Z0-9-]+)',
            r'tracking\s*(?:id|number|no\.?)\s*:?\s*([A-Z0-9-]+)',
            r'([A-Z]{2,5}\d{5,10})',
        ]

        for pattern in patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

import asyncio
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import os

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from models.models import JobListing, Application, JobFilter, ApplicationStatus

logger = logging.getLogger(__name__)

class JobAutomator:
    """Core automation class for interacting with workatastartup.com"""
    
    BASE_URL = "https://www.workatastartup.com"
    
    def __init__(self, headless: bool = False, slow_mo: int = 100):
        self.headless = headless
        self.slow_mo = slow_mo  # Slow down interactions (ms)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # State
        self.logged_in = False
        
    async def __aenter__(self):
        await self.setup()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def setup(self):
        """Initialize the browser and context"""
        logger.info("Initializing browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        
        # Create a new browser context with storage state
        self.context = await self.browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            locale='en-US',
            permissions=['geolocation'],
            record_video_dir='videos/' if os.getenv('RECORD_VIDEO', 'false').lower() == 'true' else None
        )
        
        # Grant permissions for notifications (to avoid popups)
        await self.context.grant_permissions(['notifications'])
        
        # Create a new page
        self.page = await self.context.new_page()
        
        # Enable request/response logging
        if self.page:
            self.page.on("request", lambda request: logger.debug(f"Request: {request.method} {request.url}"))
            self.page.on("response", lambda response: logger.debug(f"Response: {response.status} {response.url}"))
            
            # Handle dialog boxes
            self.page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
        
        logger.info("Browser initialized")
    
    async def close(self):
        """Close the browser and clean up"""
        logger.info("Closing browser...")
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
    
    def _ensure_page_initialized(self) -> Page:
        """Ensure the page is initialized before use"""
        if not self.page:
            raise RuntimeError("Page not initialized. Call setup() first.")
        return self.page
    
    async def login(self, email: str, password: str) -> bool:
        """Login to workatastartup.com with enhanced debugging"""
        if self.logged_in:
            return True
            
        page = self._ensure_page_initialized()
        logger.info("Starting login process...")
        
        try:
            # Navigate to the login page directly
            login_url = "https://account.ycombinator.com/?continue=https%3A%2F%2Fwww.workatastartup.com%2F"
            logger.info(f"Navigating to login page: {login_url}")
            await page.goto(login_url, wait_until="networkidle")
            
            await self._navigate_to_login_page()
            await self._fill_login_form(email, password)
            await self._submit_login_form()
            
            if await self._verify_login_success():
                self.logged_in = True
                logger.info("Login successful")
                return True
            else:
                logger.error("Login verification failed")
                await page.screenshot(path="login_verification_failed.png")
                await self._check_for_login_error_messages()
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            if self.page:
                await self.page.screenshot(path="login_error.png")
            raise

    async def _navigate_to_login_page(self):
        """Navigates to the login page and waits for the form."""
        page = self._ensure_page_initialized()
        login_url = "https://account.ycombinator.com/?continue=https%3A%2F%2Fwww.workatastartup.com%2F"
        logger.info(f"Navigating to login page: {login_url}")
        await page.goto(login_url, wait_until="networkidle")
        await page.screenshot(path="debug_login_page.png")
        logger.info("Took screenshot: debug_login_page.png")
        logger.info("Waiting for login form...")
        await page.wait_for_selector('form#sign-in-card', state="visible", timeout=10000)
        current_url = page.url
        if "account.ycombinator.com" not in current_url:
            logger.warning(f"Unexpected URL after navigation: {current_url}")

    async def _find_login_element(self, selectors: List[str], element_name: str, form_element=None) -> Optional[Any]:
        """Finds a login element using a list of selectors."""
        page = self._ensure_page_initialized()
        element_field = None
        for selector in selectors:
            try:
                if form_element:
                    element_field = await form_element.query_selector(selector)
                else:
                    element_field = await page.wait_for_selector(selector, timeout=2000, state="visible")

                if element_field and await element_field.is_editable():
                    logger.info(f"Found {element_name} input with selector: {selector}")
                    return element_field
                element_field = None  # Reset if not editable
            except Exception as e:
                logger.debug(f"{element_name.capitalize()} input selector {selector} did not work: {str(e)}")
        return None

    async def _fill_login_form(self, email: str, password: str):
        """Fills the login form with email and password."""
        page = self._ensure_page_initialized()
        email_input_selectors = [
            'input#ycid-input', 'input[name="username"]', 'input[type="email"]',
            'input[autocomplete="username"]', 'input[autocomplete="email"]',
            'input[type="text"]', 'input.MuiInput-input'
        ]
        password_input_selectors = [
            'input[type="password"]', 'input[autocomplete="current-password"]',
            'input[name="password"]', 'input#password'
        ]
        form_selectors = [
            'form#sign-in-card', 'form', 'form[action*="login"]',
            'form[action*="signin"]',
            '//form[.//input[contains(@name, "email") or contains(@type, "email") or contains(@id, "email")]]'
        ]

        email_field = await self._find_login_element(email_input_selectors, "email")
        form = None

        if not email_field:
            for form_selector in form_selectors:
                try:
                    form = await page.wait_for_selector(form_selector, timeout=2000, state="visible")
                    if form:
                        logger.info(f"Found form with selector: {form_selector}")
                        email_field = await self._find_login_element(email_input_selectors, "email", form_element=form)
                        if email_field:
                            break
                except Exception as e:
                    logger.debug(f"Form selector {form_selector} did not work: {str(e)}")

        if not email_field:
            await page.screenshot(path="login_form_not_found.png")
            logger.error("Could not find email input field on the login page")
            raise Exception("Email input not found")

        await page.screenshot(path="debug_login_form.png")
        logger.info(f"Filling in email: {email}")
        try:
            await email_field.click()
            await email_field.fill(email)
        except Exception as e:
            logger.error(f"Failed to fill email: {str(e)}")
            await page.screenshot(path="email_fill_error.png")
            raise

        password_field = await self._find_login_element(password_input_selectors, "password", form_element=form)
        if not password_field and form : # If not found globally, try within the form if form was found
             password_field = await self._find_login_element(password_input_selectors, "password", form_element=form)

        if not password_field:
            logger.error("Could not find password field")
            await page.screenshot(path="password_field_not_found.png")
            raise Exception("Password input not found")

        logger.info("Filling in password...")
        try:
            await password_field.click()
            await password_field.fill(password)
        except Exception as e:
            logger.error(f"Failed to fill password: {str(e)}")
            await page.screenshot(path="password_fill_error.png")
            raise
        await page.screenshot(path="debug_filled_form.png")

    async def _submit_login_form(self):
        """Submits the login form."""
        page = self._ensure_page_initialized()
        submit_button_selectors = 'button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")'
        submit_button = await page.wait_for_selector(submit_button_selectors, timeout=5000)
        if submit_button:
            await submit_button.click()
        else:
            await page.keyboard.press('Enter')

    async def _verify_login_success(self) -> bool:
        """Verifies if the login was successful."""
        page = self._ensure_page_initialized()
        try:
            await page.wait_for_selector(
                'a[href*="/dashboard"], a[href*="/jobs"], [data-testid="user-avatar"], img[alt*="Profile"], .user-avatar',
                timeout=15000
            )
            return True
        except Exception as e:
            logger.debug(f"Login verification element not found: {str(e)}")
            return False

    async def _check_for_login_error_messages(self):
        """Checks for and logs any login error messages."""
        page = self._ensure_page_initialized()
        error_message = await page.evaluate('''() => {
            const error = document.querySelector('.error-message, .alert-error, [role="alert"], .text-red-500, .text-red-600');
            return error ? error.innerText : null;
        }''')
        if error_message:
            logger.error(f"Login error: {error_message}")
    
    async def apply_filters(self, job_filter: JobFilter) -> bool:
        """Navigate to the pre-filtered jobs page"""
        if not self.logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        page = self._ensure_page_initialized()
        logger.info("Navigating to filtered jobs page...")
        
        try:
            # Navigate to the pre-filtered URL that contains all relevant jobs
            filtered_url = "https://www.workatastartup.com/companies?demographic=any&hasEquity=any&hasSalary=any&industry=any&interviewProcess=any&jobType=fulltime&layout=list-compact&minExperience=0&minExperience=1&role=eng&role_type=fe&role_type=fs&role_type=be&sortBy=created_desc&tab=any&usVisaNotRequired=any"
            
            await page.goto(filtered_url)
            await page.wait_for_load_state("networkidle")
            
            # Wait for the directory list to load
            await page.wait_for_selector('.directory-list', state='visible', timeout=10000)
            logger.info("Successfully navigated to filtered jobs page")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to filtered page: {str(e)}")
            if self.page:
                await self.page.screenshot(path="filter_error.png")
            raise
    
    async def get_job_listings(self, max_listings: int = 10) -> List[Dict[str, Any]]:
        """Extract job listings from the current page"""
        page = self._ensure_page_initialized()
        logger.info(f"Extracting up to {max_listings} job listings...")
        
        try:
            # Wait for the directory list to load
            await page.wait_for_selector('.directory-list', timeout=10000)
            
            await self._scroll_to_load_jobs(max_listings)
            jobs = await self._extract_job_data_from_page()
            
            # Filter out invalid jobs and limit to max_listings
            valid_jobs = [
                job for job in jobs
                if job.get('url') and job.get('title') and job.get('title') != 'Untitled Position'
            ]
            limited_jobs = valid_jobs[:max_listings]
            
            logger.info(f"Found {len(limited_jobs)} jobs")
            return limited_jobs
            
        except Exception as e:
            logger.error(f"Failed to get job listings: {str(e)}")
            if self.page:
                await self.page.screenshot(path="job_listings_error.png")
            raise

    async def _scroll_to_load_jobs(self, max_listings: int):
        """Scrolls the page to load job listings dynamically."""
        page = self._ensure_page_initialized()
        last_height = await page.evaluate('document.body.scrollHeight')
        job_selector = '.bg-beige-lighter.mb-5.rounded.pb-4'

        while len(await page.query_selector_all(job_selector)) < max_listings:
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(1.5) # Wait for content to load

            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                break # Reached end of page
            last_height = new_height

            if len(await page.query_selector_all(job_selector)) >= max_listings:
                break

    async def _extract_job_data_from_page(self) -> List[Dict[str, Any]]:
        """Extracts job data from the current page content using the specific HTML structure."""
        page = self._ensure_page_initialized()
        return await page.evaluate("""() => {
            const jobContainers = document.querySelectorAll('.bg-beige-lighter.mb-5.rounded.pb-4');
            const jobs = [];

            jobContainers.forEach(container => {
                // Extract company information
                const companyNameEl = container.querySelector('.company-name');
                const companyName = companyNameEl ? companyNameEl.textContent.trim() : 'Unknown Company';
                
                const companyBatchEl = container.querySelector('.text-gray-400');
                const companyBatch = companyBatchEl ? companyBatchEl.textContent.trim() : '';
                
                const companyDescriptionEl = container.querySelector('.text-gray-700');
                const companyDescription = companyDescriptionEl ? companyDescriptionEl.textContent.trim() : '';
                
                // Extract company links
                const websiteEl = container.querySelector('a[href*="/website"]');
                const website = websiteEl ? websiteEl.href : '';
                
                const twitterEl = container.querySelector('a[href*="twitter.com"], a[href*="x.com"]');
                const twitter = twitterEl ? twitterEl.href : '';
                
                // Extract company details (location, size, industry)
                const detailLabels = container.querySelectorAll('.detail-label');
                const details = Array.from(detailLabels).map(label => label.textContent.trim());
                
                // Extract all job listings within this company container
                const jobElements = container.querySelectorAll('.job-name a[href*="/jobs/"]');
                
                jobElements.forEach(jobEl => {
                    const jobUrl = jobEl.href;
                    const jobTitle = jobEl.textContent.trim();
                    
                    // Extract job ID from URL
                    const jobIdMatch = jobUrl.match(/\\/jobs\\/(\\d+)/);
                    const jobId = jobIdMatch ? jobIdMatch[1] : `job-${Math.random().toString(36).substring(2, 9)}`;
                    
                    // Find the parent job container to get metadata
                    const jobContainer = jobEl.closest('.mb-4');
                    const metadataElements = jobContainer ? jobContainer.querySelectorAll('.mr-2.text-sm span') : [];
                    const metadata = Array.from(metadataElements).map(el => el.textContent.trim());
                    
                    // Extract salary, equity, experience from metadata
                    let salary = '', equity = '', experience = '', location = '', jobType = '', visa = '';
                    metadata.forEach((meta, index) => {
                        if (meta.includes('$') || meta.includes('€') || meta.includes('K')) {
                            salary = meta;
                        } else if (meta.includes('%')) {
                            equity = meta;
                        } else if (meta.includes('years') || meta.includes('grads')) {
                            experience = meta;
                        } else if (meta.includes(',') && (meta.includes('US') || meta.includes('GB') || meta.includes('ES') || meta.includes('IN'))) {
                            location = meta;
                        } else if (meta === 'fulltime' || meta === 'parttime') {
                            jobType = meta;
                        } else if (meta.includes('visa') || meta.includes('citizen') || meta.includes('sponsor')) {
                            visa = meta;
                        }
                    });
                    
                    // Find the "View job" button
                    const viewJobButton = jobContainer ? jobContainer.querySelector('a.rounded-md.bg-brand') : null;
                    const viewJobUrl = viewJobButton ? viewJobButton.href : jobUrl;
                    
                    // Check if there's an "Apply" button (for companies without specific jobs)
                    const applyButton = container.querySelector('a.bg-orange-500, button.bg-orange-500');
                    const hasApplyButton = !!applyButton;
                    
                    // Extract company logo
                    const logoEl = container.querySelector('img[alt]');
                    const logoUrl = logoEl ? logoEl.src : '';
                    const logoAlt = logoEl ? logoEl.alt : '';
                    
                    const jobData = {
                        id: jobId,
                        title: jobTitle,
                        company: {
                            name: companyName,
                            batch: companyBatch,
                            description: companyDescription,
                            website: website,
                            twitter: twitter,
                            logo: {
                                url: logoUrl,
                                alt: logoAlt
                            },
                            details: details
                        },
                        location: location,
                        salary: salary,
                        equity: equity,
                        experience: experience,
                        jobType: jobType,
                        visa: visa,
                        url: jobUrl,
                        viewJobUrl: viewJobUrl,
                        hasApplyButton: hasApplyButton,
                        metadata: metadata,
                        extractedAt: new Date().toISOString()
                    };
                    
                    jobs.push(jobData);
                });
                
                // Handle companies with no specific jobs but have an "Apply" button
                if (jobElements.length === 0 && hasApplyButton) {
                    const applyUrl = applyButton.href || '';
                    
                    const generalJobData = {
                        id: `general-${companyName.toLowerCase().replace(/\\s+/g, '-')}`,
                        title: `General Application - ${companyName}`,
                        company: {
                            name: companyName,
                            batch: companyBatch,
                            description: companyDescription,
                            website: website,
                            twitter: twitter,
                            logo: {
                                url: logoUrl,
                                alt: logoAlt
                            },
                            details: details
                        },
                        location: details.find(d => d.includes(',')) || '',
                        salary: '',
                        equity: '',
                        experience: '',
                        jobType: 'fulltime',
                        visa: '',
                        url: applyUrl,
                        viewJobUrl: applyUrl,
                        hasApplyButton: true,
                        metadata: details,
                        extractedAt: new Date().toISOString()
                    };
                    
                    jobs.push(generalJobData);
                }
            });
            
            return jobs;
        }""")
    
    async def process_job_application(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single job application (test mode - doesn't submit)"""
        if not self.logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        page = self._ensure_page_initialized()
        logger.info(f"Processing job application: {job.get('title', 'Unknown')}")
        
        try:
            # Navigate to job page
            logger.info(f"Navigating to job page: {job.get('url')}")
            await page.goto(job['url'])
            await page.wait_for_load_state("networkidle")
            
            await page.screenshot(path=f"job_page_{job.get('id', 'unknown')}.png")
            
            job_details = await self._extract_job_details()
            full_job_info = self._compile_full_job_info(job, job_details)
            self._save_job_details_for_debugging(full_job_info)
            
            logger.info(f"Successfully extracted job details. Title: {job.get('title', 'Unknown')}")
            
            cover_letter = await self.generate_cover_letter(full_job_info)
            self._save_cover_letter(cover_letter, job.get('id', 'unknown'))
            self._log_generated_cover_letter(cover_letter)
            
            await self._find_and_log_apply_button()
            
            logger.info("TEST MODE: Application not submitted (test mode)")
            
            return self._create_application_result(full_job_info, cover_letter, status="test_mode", success=True, test_mode=True)
            
        except Exception as e:
            logger.error(f"Failed to process job application: {str(e)}", exc_info=True)
            if self.page:
                await self.page.screenshot(path=f"error_{job.get('id', 'unknown')}.png")
                
                # Save the page HTML for debugging
                try:
                    html_content = await self.page.content()
                    with open(f"error_page_{job.get('id', 'unknown')}.html", 'w', encoding='utf-8') as f:
                        f.write(html_content)
                except Exception as html_err:
                    logger.error(f"Failed to save page HTML: {str(html_err)}")
            
            return {
                **job,
                "status": "error",
                "success": False,
                "error": str(e),
                "job_id": job.get('id', 'unknown')
            }

    async def _extract_job_details(self) -> Dict[str, str]:
        """Extracts full job description and HTML content from the job page."""
        self._ensure_page_initialized()
        return await self.page.evaluate("""() => {
            const descriptionSelectors = [
                '.job-description', '.job-description-content', '[data-testid="job-description"]',
                'div[class*="description"]', 'div[class*="Description"]', 'section[class*="description"]',
                'div[itemprop="description"]', 'div.job-details', 'div.description', 'div.jobDescription',
                'div.job-description-text', 'div.job-details-content', 'div.job-details-container',
                'div.job-content', 'div.job-body', 'div.job-page', 'div.job-container', 'div.job-listing',
                'div.job', 'article.job', 'section.job', 'div[role="main"]', 'main', 'article', 'section',
                'div.container', 'div.main-content', 'div.content', 'div#content', 'div#main', 'div#job',
                'div#job-details', 'div#job-description', 'div#job-content', 'div#job-body', 'div#job-page',
                'div#job-container', 'div#job-listing', 'div#job-description-content', 'div#job-details-content',
                'div#job-description-text', 'div#job-details-container', 'div#job-content-container',
                'div#main-content', 'div#content-container', 'div#main-container', 'div#container',
                'div#page', 'div#app', 'div#root', 'body', 'html'
            ];
            let mainContent = null;
            for (const selector of descriptionSelectors) {
                const elements = Array.from(document.querySelectorAll(selector));
                elements.sort((a, b) => (b.offsetWidth * b.offsetHeight) - (a.offsetWidth * a.offsetHeight));
                for (const el of elements) {
                    if (el.innerText && el.innerText.trim().length > 100) {
                        mainContent = el;
                        break;
                    }
                }
                if (mainContent) break;
            }
            if (mainContent) {
                return {
                    full_description: mainContent.innerText.trim(),
                    html_content: mainContent.innerHTML,
                    found_using: mainContent.tagName.toLowerCase() + (mainContent.id ? '#' + mainContent.id : '') + (mainContent.className ? '.' + mainContent.className.replace(/\\s+/g, '.') : '')
                };
            }
            return {
                full_description: document.body.innerText,
                html_content: document.documentElement.outerHTML,
                found_using: 'fallback:document.body'
            };
        }""")

    def _compile_full_job_info(self, job: Dict[str, Any], job_details: Dict[str, str]) -> Dict[str, Any]:
        """Combines initial job info with extracted details."""
        return {**job, **job_details, "scraped_at": datetime.utcnow().isoformat()}

    def _save_job_details_for_debugging(self, full_job_info: Dict[str, Any]):
        """Saves the full job information to a JSON file for debugging."""
        job_id = full_job_info.get('id', 'unknown')
        try:
            with open(f"job_{job_id}.json", 'w', encoding='utf-8') as f:
                import json
                json.dump(full_job_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save job details for {job_id}: {str(e)}")

    def _save_cover_letter(self, cover_letter: str, job_id: str):
        """Saves the generated cover letter to a text file."""
        try:
            with open(f"cover_letter_{job_id}.txt", 'w', encoding='utf-8') as f:
                f.write(cover_letter)
        except Exception as e:
            logger.error(f"Failed to save cover letter for {job_id}: {str(e)}")

    def _log_generated_cover_letter(self, cover_letter: str):
        """Logs the generated cover letter."""
        logger.info("\n" + "="*80 + "\nGENERATED COVER LETTER:\n" + "-"*80 + f"\n{cover_letter}\n" + "="*80 + "\n")

    async def _find_and_log_apply_button(self):
        """Finds the apply button and logs its presence or alternatives."""
        self._ensure_page_initialized()
        apply_button_texts = [
            "Apply Now", "Apply", "Apply for this job", "Apply for position",
            "Submit application", "Apply with Indeed", "Apply with LinkedIn",
            "Quick apply", "Apply for this position", "Apply with resume"
        ]
        apply_button = None
        for btn_text in apply_button_texts:
            try:
                # Use a more specific selector if possible, e.g., button or a with role="button"
                button_selector = f'button:has-text("{btn_text}"), a[role="button"]:has-text("{btn_text}")'
                # Wait for a short period to see if the button appears
                current_button = await self.page.wait_for_selector(button_selector, timeout=1000, state="visible")
                if current_button: # Check if it's visible and enabled (or whatever criteria you need)
                    logger.info(f"Found apply button with text: '{btn_text}'")
                    apply_button = current_button
                    break
            except Exception: # TimeoutError if not found within timeout
                logger.debug(f"Apply button with text '{btn_text}' not found or not visible/enabled quickly.")
                continue # Try next button text

        if not apply_button:
            logger.warning("No primary apply button found. Logging page button structure for debugging.")
            await self._log_page_button_structure()
        else:
            logger.info("Apply button found (not clicking in test mode).")

    async def _log_page_button_structure(self):
        """Logs the structure of all buttons on the page for debugging."""
        self._ensure_page_initialized()
        page_structure = await self.page.evaluate("""() => {
            function getPath(element) {
                if (!element || !element.tagName) return '';
                const path = [];
                while (element.nodeType === Node.ELEMENT_NODE) {
                    let selector = element.tagName.toLowerCase();
                    if (element.id) { selector += '#' + element.id; path.unshift(selector); break; }
                    else {
                        let sib = element, nth = 1;
                        while (sib = sib.previousElementSibling) { if (sib.tagName.toLowerCase() === selector) nth++; }
                        if (nth > 1) selector += ':nth-of-type(' + nth + ')';
                    }
                    path.unshift(selector);
                    element = element.parentNode;
                }
                return path.join(' > ');
            }
            const buttons = [];
            document.querySelectorAll('button, a[role="button"], input[type="button"], input[type="submit"]').forEach(btn => {
                buttons.push({
                    text: btn.innerText.replace(/\\s+/g, ' ').trim(), tag: btn.tagName,
                    id: btn.id || '', classes: btn.className || '', path: getPath(btn)
                });
            });
            return buttons;
        }""")
        logger.info("Page buttons:")
        for btn in page_structure:
            if btn['text']:
                logger.info(f"- {btn['text']} (tag: {btn['tag']}, id: {btn['id']}, classes: {btn['classes']}) Path: {btn['path']}")

    def _create_application_result(self, full_job_info: Dict[str, Any], cover_letter: str, status: str, success: bool, test_mode: bool = False, error: Optional[str] = None) -> Dict[str, Any]:
        """Creates a structured result for the job application process."""
        result = {
            **full_job_info,
            "status": status,
            "success": success,
            "cover_letter": cover_letter,
            "applied_at": datetime.utcnow().isoformat() if success else None,
            "test_mode": test_mode
        }
        if error:
            result["error"] = error
        return result
    
    async def generate_cover_letter(self, job_info: Dict[str, Any]) -> str:
        """Generate a personalized cover letter for the job using job details"""
        logger.info("Generating cover letter...")
        
        try:
            job_title = job_info.get('title', 'this position')
            company_name = job_info.get('company', 'your company')
            
            requirements, responsibilities = self._extract_requirements_and_responsibilities(job_info)

            cover_letter_template = self._get_cover_letter_template()

            formatted_letter = cover_letter_template.format(
                job_title=job_title,
                company_name=company_name,
                requirements_section=self._format_list_section(requirements, "Strong problem-solving skills and a passion for technology"),
                responsibilities_section=self._format_list_section(responsibilities, "I'm eager to bring my skills to help achieve company goals.", transform_func=self._transform_responsibility_to_first_person),
                your_field="software engineering",
                relevant_skills="Python, web development, and problem-solving",
                relevant_experience="building scalable applications",
                specific_aspect_company=f'the innovative work {company_name} is doing',
                specific_reason="I admire your commitment to excellence", # Generic, can be improved
                specific_contribution="contribute to your team",
                specific_impact="drive meaningful results",
                your_name="[Your Name]" # Placeholder for actual name
            )
            return formatted_letter
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            return self._get_fallback_cover_letter(job_info)

    def _extract_requirements_and_responsibilities(self, job_info: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Extracts key requirements and responsibilities from job description."""
        job_description = job_info.get('full_description', '')
        lines = job_description.split('\n')
        requirements, responsibilities = [], []

        req_indicators = ['requirement', 'qualification', 'skill', 'experience', 'proficiency', 'knowledge of', 'familiar with']
        resp_indicators = ['responsibilit', 'dutie', 'you will', 'role will', 'key function']

        for line in lines:
            line = line.strip()
            if not line: continue
            if any(indicator in line.lower() for indicator in req_indicators):
                requirements.append(line)
            elif any(indicator in line.lower() for indicator in resp_indicators):
                responsibilities.append(line)

        return requirements[:5], responsibilities[:5]

    def _get_cover_letter_template(self) -> str:
        """Returns the cover letter template string."""
        return """Dear Hiring Manager,

I'm excited to apply for the {job_title} position at {company_name}. With my background in {your_field}, I'm confident in my ability to contribute effectively to your team.

### Why I'm a Great Fit
I noticed that you're looking for someone with:
{requirements_section}

### How I Can Add Value
{responsibilities_section}

### Why {company_name}
I'm particularly drawn to {specific_aspect_company} because {specific_reason}. I'm excited about the opportunity to {specific_contribution} and help {specific_impact}.

I'd welcome the opportunity to discuss how my background and skills align with your needs. Thank you for your time and consideration.

Best regards,
{your_name}"""

    def _format_list_section(self, items: List[str], default_text: str, transform_func: Optional[callable] = None) -> str:
        """Formats a list of items into a bulleted string section for the cover letter."""
        if not items:
            return f"- {default_text}\n"

        section_str = ""
        for item in items:
            processed_item = transform_func(item) if transform_func else item
            section_str += f"- {processed_item}\n"
        return section_str

    def _transform_responsibility_to_first_person(self, resp_text: str) -> str:
        """Transforms a responsibility statement to the first person."""
        resp_text_lower = resp_text.lower()
        for pronoun in ['you will', 'the candidate will', 'they will']:
            if pronoun in resp_text_lower:
                resp_text_lower = resp_text_lower.replace(pronoun, 'I can')
        return resp_text_lower.capitalize() if resp_text_lower else ""

    def _get_fallback_cover_letter(self, job_info: Dict[str, Any]) -> str:
        """Returns a fallback cover letter template."""
        return f"""Dear Hiring Manager,
I'm excited to apply for the {job_info.get('title', 'position')} at {job_info.get('company', 'your company')}.
I believe my skills and experience make me a strong candidate for this role.
Looking forward to the opportunity to discuss how I can contribute to your team.
Best regards,
[Your Name]"""

    async def run(self, email: str, password: str, max_applications: int = 5) -> Dict[str, Any]:
        """
        Run the complete automation workflow.

        Args:
            email: User's email for login.
            password: User's password for login.
            max_applications: Maximum number of job applications to process.

        Returns:
            A dictionary containing the results of the automation run.
        """
        results: Dict[str, Any] = {
            "start_time": datetime.utcnow().isoformat(),
            "applications": [],
            "success_count": 0,
            "error_count": 0
        }
        
        try:
            # Set up browser
            await self.setup()
            
            # Login
            login_success = await self.login(email, password)
            if not login_success:
                raise Exception("Login failed")
            
            # Apply filters
            job_filter = JobFilter()
            await self.apply_filters(job_filter)
            
            # Get job listings
            jobs = await self.get_job_listings(max_listings=max_applications)
            
            # Process each job
            for job in jobs:
                result = await self.process_job_application(job)
                results["applications"].append(result)
                
                if result.get("success"):
                    results["success_count"] += 1
                else:
                    results["error_count"] += 1
                
                # Add a small delay between applications
                await asyncio.sleep(5)
            
            results["status"] = "completed"
            
        except Exception as e:
            logger.error(f"Automation failed: {str(e)}")
            results["status"] = "failed"
            results["error"] = str(e)
            
        finally:
            # Clean up
            await self.close()
            results["end_time"] = datetime.utcnow().isoformat()
            
        return results

    async def click_send_message_button(self):
        """
        Clicks the 'Send message' button on a job application page.
        Note: This method is not yet used in the main workflow.
        """
        self._ensure_page_initialized()

        logger.info("Attempting to click the 'Send message' button...")
        try:
            # Common selectors for a "Send Message" button. These might need adjustment.
            send_message_selectors = [
                'button:has-text("Send Message")',
                'button:has-text("Send message")',
                'button[data-testid*="send-message"]',
                'button[aria-label*="Send Message"]',
                'button[title*="Send Message"]'
            ]

            send_button = None
            for selector in send_message_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, state="visible", timeout=5000)
                    if button and await button.is_enabled():
                        send_button = button
                        logger.info(f"Found 'Send message' button with selector: {selector}")
                        break
                except Exception:
                    logger.debug(f"'Send message' button not found with selector: {selector}")

            if not send_button:
                logger.warning("Could not find an enabled 'Send message' button on the page.")
                await self.page.screenshot(path="send_message_button_not_found.png")
                # Optionally, log page structure here if needed for debugging
                return False

            await send_button.click()
            logger.info("'Send message' button clicked successfully.")
            # Add verification step if possible, e.g., wait for a confirmation or modal.
            # await self.page.wait_for_selector("text=Message Sent", timeout=5000)
            return True

        except Exception as e:
            logger.error(f"Failed to click 'Send message' button: {str(e)}")
            if self.page:
                await self.page.screenshot(path="send_message_button_error.png")
            return False

    async def click_view_job_button(self, job_index: int = 0):
        """
        Clicks a 'View job' button on the job search results page.
        These are typically orange buttons with white text.

        Args:
            job_index: The index of the 'View job' button to click (0-based).
                       Defaults to the first button found.
        """
        self._ensure_page_initialized()

        logger.info(f"Attempting to click 'View job' button at index {job_index}...")
        try:
            # Selectors for "View job" buttons. These are common patterns.
            # The key is to find a selector that uniquely identifies these buttons,
            # possibly by text, color (though harder with CSS), or data attributes.
            view_job_selectors = [
                'a:has-text("View Job")',  # Anchor tag with text "View Job"
                'button:has-text("View Job")', # Button with text "View Job"
                'a.orange-button:has-text("View Job")', # Example if it has a specific class
                '[data-testid*="view-job-button"]', # If it has a test ID
                '//a[contains(translate(., "VIEWJOB", "viewjob"), "view job") and contains(@class, "button")]', # XPath for case-insensitive text and class
                '//button[contains(translate(., "VIEWJOB", "viewjob"), "view job")]' # XPath for case-insensitive text
            ]

            view_job_buttons = []
            for selector in view_job_selectors:
                try:
                    buttons = await self.page.query_selector_all(selector)
                    visible_buttons = []
                    for btn in buttons:
                        if await btn.is_visible() and await btn.is_enabled():
                             visible_buttons.append(btn)

                    if visible_buttons: # If this selector yields any visible and enabled buttons
                        view_job_buttons = visible_buttons
                        logger.info(f"Found {len(view_job_buttons)} 'View job' button(s) with selector: {selector}")
                        break # Use the first selector that finds buttons
                except Exception as e:
                    logger.debug(f"Selector {selector} for 'View job' button failed or found no elements: {str(e)}")

            if not view_job_buttons:
                logger.warning("No 'View job' buttons found on the page.")
                await self.page.screenshot(path="view_job_button_not_found.png")
                return False

            if job_index >= len(view_job_buttons):
                logger.warning(f"'View job' button index {job_index} is out of range. Found {len(view_job_buttons)} buttons.")
                await self.page.screenshot(path="view_job_button_index_error.png")
                return False

            target_button = view_job_buttons[job_index]

            # Scroll into view if necessary
            await target_button.scroll_into_view_if_needed()

            await target_button.click()
            logger.info(f"'View job' button at index {job_index} clicked successfully.")

            # Wait for navigation or content change that indicates success
            await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            # Potentially wait for a specific element on the job details page
            # await self.page.wait_for_selector(".job-description", timeout=10000)
            logger.info("Navigation after 'View job' click seems successful.")
            return True

        except Exception as e:
            logger.error(f"Failed to click 'View job' button at index {job_index}: {str(e)}")
            if self.page:
                await self.page.screenshot(path="view_job_button_error.png")
            return False
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
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("Browser closed")
    
    async def login(self, email: str, password: str) -> bool:
        """Login to workatastartup.com with enhanced debugging"""
        if self.logged_in:
            return True
            
        logger.info("Starting login process...")
        
        try:
            # Navigate to the login page directly
            login_url = "https://account.ycombinator.com/?continue=https%3A%2F%2Fwww.workatastartup.com%2F"
            logger.info(f"Navigating to login page: {login_url}")
            await self.page.goto(login_url, wait_until="networkidle")
            
            # Take a screenshot for debugging
            await self.page.screenshot(path="debug_login_page.png")
            logger.info("Took screenshot: debug_login_page.png")
            
            # Wait for the login form to be visible
            logger.info("Waiting for login form...")
            await self.page.wait_for_selector('form#sign-in-card', state="visible", timeout=10000)
            
            # Check if we're on the right page
            current_url = self.page.url
            if "account.ycombinator.com" not in current_url:
                logger.warning(f"Unexpected URL after navigation: {current_url}")
            email_input_selectors = [
                'input#ycid-input',  # YC specific email input
                'input[name="username"]',
                'input[type="email"]',
                'input[autocomplete="username"]',
                'input[autocomplete="email"]',
                'input[type="text"]',
                'input.MuiInput-input'
            ]
            
            password_input_selectors = [
                'input[type="password"]',
                'input[autocomplete="current-password"]',
                'input[name="password"]',
                'input#password'
            ]
            
            # First, try to find the email input field directly
            email_field = None
            for selector in email_input_selectors:
                try:
                    email_field = await self.page.wait_for_selector(selector, timeout=2000, state="visible")
                    if email_field and await email_field.is_editable():
                        logger.info(f"Found email input with selector: {selector}")
                        break
                    email_field = None
                except Exception as e:
                    logger.debug(f"Email input selector {selector} did not work: {str(e)}")
            
            if not email_field:
                # Try to find the form and then look for inputs within it
                form_selectors = [
                    'form#sign-in-card',
                    'form',
                    'form[action*="login"]',
                    'form[action*="signin"]',
                    '//form[.//input[contains(@name, "email") or contains(@type, "email") or contains(@id, "email")]]'
                ]
                
                for form_selector in form_selectors:
                    try:
                        form = await self.page.wait_for_selector(form_selector, timeout=2000, state="visible")
                        if form:
                            logger.info(f"Found form with selector: {form_selector}")
                            # Look for email input within this form
                            for email_selector in email_input_selectors:
                                try:
                                    email_field = await form.query_selector(email_selector)
                                    if email_field and await email_field.is_editable():
                                        logger.info(f"Found email input in form with selector: {email_selector}")
                                        break
                                    email_field = None
                                except Exception as e:
                                    logger.debug(f"Form email selector {email_selector} did not work: {str(e)}")
                            if email_field:
                                break
                    except Exception as e:
                        logger.debug(f"Form selector {form_selector} did not work: {str(e)}")
            
            if not email_field:
                # Take a screenshot of the current page for debugging
                await self.page.screenshot(path="login_form_not_found.png")
                logger.error("Could not find email input field on the login page")
                logger.info("Saved screenshot: login_form_not_found.png")
                
                # Log the current URL and page title for debugging
                logger.info(f"Current URL: {self.page.url}")
                logger.info(f"Page title: {await self.page.title()}")
                
                # Try to get the page HTML for debugging
                try:
                    page_html = await self.page.content()
                    with open("page_content.html", "w", encoding="utf-8") as f:
                        f.write(page_html)
                    logger.info("Saved page content to: page_content.html")
                except Exception as e:
                    logger.error(f"Failed to save page content: {str(e)}")
                
                return False
            
            # Take a screenshot of the login form
            await self.page.screenshot(path="debug_login_form.png")
            logger.info("Took screenshot: debug_login_form.png")
            
            # Fill in login form with more detailed logging
            logger.info(f"Filling in email: {email}")
            try:
                await email_field.click()
                await email_field.fill(email)
                logger.info("Successfully filled email")
            except Exception as e:
                logger.error(f"Failed to fill email: {str(e)}")
                await self.page.screenshot(path="email_fill_error.png")
                return False
            
            # Find and fill password field
            password_field = None
            for selector in password_input_selectors:
                try:
                    password_field = await self.page.wait_for_selector(selector, timeout=3000, state="visible")
                    if password_field and await password_field.is_editable():
                        logger.info(f"Found password field with selector: {selector}")
                        break
                    password_field = None
                except Exception as e:
                    logger.debug(f"Password field selector {selector} did not work: {str(e)}")
            
            if not password_field:
                # Try to find password field within the form
                if form:
                    for selector in password_input_selectors:
                        try:
                            password_field = await form.query_selector(selector)
                            if password_field and await password_field.is_editable():
                                logger.info(f"Found password field in form with selector: {selector}")
                                break
                            password_field = None
                        except Exception as e:
                            logger.debug(f"Form password selector {selector} did not work: {str(e)}")
            
            if not password_field:
                logger.error("Could not find password field")
                await self.page.screenshot(path="password_field_not_found.png")
                logger.info("Saved screenshot: password_field_not_found.png")
                
                # Try to get the page HTML for debugging
                try:
                    page_html = await self.page.content()
                    with open("password_page_content.html", "w", encoding="utf-8") as f:
                        f.write(page_html)
                    logger.info("Saved page content to: password_page_content.html")
                except Exception as e:
                    logger.error(f"Failed to save page content: {str(e)}")
                    
                return False
                
            logger.info("Filling in password...")
            try:
                await password_field.click()
                await password_field.fill(password)
                logger.info("Successfully filled password")
            except Exception as e:
                logger.error(f"Failed to fill password: {str(e)}")
                await self.page.screenshot(path="password_fill_error.png")
                return False
            
            # Take a screenshot after filling the form
            await self.page.screenshot(path="debug_filled_form.png")
            logger.info("Took screenshot: debug_filled_form.png")
            
            # Click the submit button
            submit_button = await self.page.wait_for_selector('button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")', timeout=5000)
            if submit_button:
                await submit_button.click()
            else:
                # Try pressing Enter if button not found
                await self.page.keyboard.press('Enter')
            
            # Wait for login to complete (look for dashboard, jobs, or user avatar)
            try:
                await self.page.wait_for_selector(
                    'a[href*="/dashboard"], a[href*="/jobs"], [data-testid="user-avatar"], img[alt*="Profile"], .user-avatar', 
                    timeout=15000
                )
                self.logged_in = True
                logger.info("Login successful")
                return True
                
            except Exception as e:
                logger.error(f"Login verification failed: {str(e)}")
                await self.page.screenshot(path="login_verification_failed.png")
                
                # Check for error messages
                error_message = await self.page.evaluate('''() => {
                    const error = document.querySelector('.error-message, .alert-error, [role="alert"], .text-red-500, .text-red-600');
                    return error ? error.innerText : null;
                }''')
                
                if error_message:
                    logger.error(f"Login error: {error_message}")
                
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            if self.page:
                await self.page.screenshot(path="login_error.png")
            raise
    
    async def apply_filters(self, job_filter: JobFilter) -> bool:
        """Apply job search filters"""
        if not self.page or not self.logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        logger.info("Applying filters...")
        
        try:
            # Navigate to jobs page
            await self.page.goto(f"{self.BASE_URL}/jobs")
            await self.page.wait_for_load_state("networkidle")
            
            # Apply experience filter (0-1 years)
            await self.page.click('button:has-text("Experience Level")')
            await self.page.click(f'button:has-text("{job_filter.experience_level}")')
            
            # Apply role filters
            for role in job_filter.roles:
                await self.page.click('button:has-text("Role")')
                await self.page.click(f'button:has-text("{role}")')
            
            # Apply remote filter if needed
            if job_filter.remote_only:
                await self.page.click('button:has-text("Remote")')
            
            # Wait for results to load
            await self.page.wait_for_selector('.job-listing', state='visible')
            logger.info("Filters applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply filters: {str(e)}")
            if self.page:
                await self.page.screenshot(path="filter_error.png")
            raise
    
    async def get_job_listings(self, max_listings: int = 10) -> List[Dict[str, Any]]:
        """Extract job listings from the current page"""
        if not self.page:
            raise RuntimeError("Browser not initialized. Call setup() first.")
            
        logger.info(f"Extracting up to {max_listings} job listings...")
        
        try:
            # Wait for job listings to load
            await self.page.wait_for_selector('.job-card, [data-testid="job-card"], .job-listing, .job-item', timeout=10000)
            
            # Scroll to load all jobs (lazy loading)
            last_height = 0
            current_height = await self.page.evaluate('document.body.scrollHeight')
            
            while len(await self.page.query_selector_all('.job-card, [data-testid="job-card"], .job-listing, .job-item')) < max_listings:
                # Scroll to the bottom of the page
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                
                # Wait for content to load
                await asyncio.sleep(1.5)
                
                # Calculate new scroll height and compare with last scroll height
                new_height = await self.page.evaluate('document.body.scrollHeight')
                if new_height == last_height:
                    # If heights are the same, we've reached the end of the page
                    break
                    
                last_height = new_height
                
                # Stop if we have enough jobs
                if len(await self.page.query_selector_all('.job-card, [data-testid="job-card"], .job-listing, .job-item')) >= max_listings:
                    break
            
            # Extract job data with more robust selectors
            jobs = await self.page.evaluate("""() => {
                const jobSelectors = [
                    '.job-card', 
                    '[data-testid="job-card"]', 
                    '.job-listing', 
                    '.job-item',
                    'div[class*="job"], article[class*="job"]',
                    'div[data-cy*="job"], article[data-cy*="job"]',
                    'div[data-test*="job"], article[data-test*="job"]',
                    'div[role="article"]',
                    'div[itemtype*="JobPosting"]',
                    'div[itemscope][itemtype*="JobPosting"]'
                ];
                
                // Find all job elements
                const jobElements = [];
                for (const selector of jobSelectors) {
                    const elements = document.querySelectorAll(selector);
                    for (const el of elements) {
                        // Skip if already added or doesn't look like a job card
                        if (!jobElements.includes(el) && 
                            (el.innerText.length > 50 || 
                             el.querySelector('a[href*="job"], a[href*="jobs"]'))) {
                            jobElements.push(el);
                        }
                    }
                    if (jobElements.length >= 30) break; // Don't collect too many
                }
                
                // Extract data from each job element
                return jobElements.map(job => {
                    // Try to find the job title
                    const titleEl = job.querySelector('[data-qa*="job-title"], [data-test*="job-title"], h2, h3, .job-title, .title');
                    
                    // Try to find company name
                    const companyEl = job.querySelector('[data-qa*="company"], [data-test*="company"], .company, .company-name, .employer');
                    
                    // Try to find location
                    const locationEl = job.querySelector('[data-qa*="location"], [data-test*="location"], .location, .job-location, .job-metadata');
                    
                    // Try to find the job URL
                    let url = '';
                    const linkEl = job.querySelector('a[href*="job"], a[href*="jobs"]');
                    if (linkEl) {
                        url = linkEl.href;
                        // Make sure URL is absolute
                        if (url.startsWith('/')) {
                            url = window.location.origin + url;
                        }
                    }
                    
                    // Get the job ID from URL or data attributes
                    let jobId = '';
                    if (url) {
                        const match = url.match(/\/jobs?\/(\d+)/) || url.match(/\/jobs?\/[^/]+-(\d+)/);
                        if (match && match[1]) {
                            jobId = match[1];
                        }
                    }
                    
                    // Fallback to data attributes for ID
                    if (!jobId) {
                        jobId = job.getAttribute('data-job-id') || 
                                job.getAttribute('id') || 
                                job.closest('[data-job-id]')?.getAttribute('data-job-id') || '';
                    }
                    
                    // Get description (first 200 chars of visible text)
                    const description = job.innerText.trim().substring(0, 200) + (job.innerText.length > 200 ? '...' : '');
                    
                    return {
                        id: jobId || `job-${Math.random().toString(36).substr(2, 9)}`,
                        title: titleEl ? titleEl.innerText.trim() : 'Untitled Position',
                        company: companyEl ? companyEl.innerText.trim() : 'Unknown Company',
                        location: locationEl ? locationEl.innerText.trim() : 'Remote',
                        url: url,
                        description: description
                    };
                });
            }""")
            
            # Filter out invalid jobs and limit to max_listings
            jobs = [job for job in jobs if job.get('url') and job.get('title') and job.get('title') != 'Untitled Position']
            jobs = jobs[:max_listings]
            
            logger.info(f"Found {len(jobs)} jobs")
            return jobs
            
        except Exception as e:
            logger.error(f"Failed to get job listings: {str(e)}")
            if self.page:
                await self.page.screenshot(path="job_listings_error.png")
            raise
    
    async def process_job_application(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single job application (test mode - doesn't submit)"""
        if not self.page or not self.logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        logger.info(f"Processing job application: {job.get('title', 'Unknown')}")
        
        try:
            # Navigate to job page
            logger.info(f"Navigating to job page: {job.get('url')}")
            await self.page.goto(job['url'])
            await self.page.wait_for_load_state("networkidle")
            
            # Take a screenshot for debugging
            await self.page.screenshot(path=f"job_page_{job.get('id', 'unknown')}.png")
            
            # Extract full job description using more robust selectors
            job_details = await self.page.evaluate("""() => {
                // Try multiple selectors for job description
                const descriptionSelectors = [
                    '.job-description',
                    '.job-description-content',
                    '[data-testid="job-description"]',
                    'div[class*="description"]',
                    'div[class*="Description"]',
                    'section[class*="description"]',
                    'div[itemprop="description"]',
                    'div.job-details',
                    'div.description',
                    'div.jobDescription',
                    'div.job-description-text',
                    'div.job-details-content',
                    'div.job-details-container',
                    'div.job-content',
                    'div.job-body',
                    'div.job-page',
                    'div.job-container',
                    'div.job-listing',
                    'div.job',
                    'article.job',
                    'section.job',
                    'div[role="main"]',
                    'main',
                    'article',
                    'section',
                    'div.container',
                    'div.main-content',
                    'div.content',
                    'div#content',
                    'div#main',
                    'div#job',
                    'div#job-details',
                    'div#job-description',
                    'div#job-content',
                    'div#job-body',
                    'div#job-page',
                    'div#job-container',
                    'div#job-listing',
                    'div#job-description-content',
                    'div#job-details-content',
                    'div#job-description-text',
                    'div#job-details-container',
                    'div#job-content-container',
                    'div#main-content',
                    'div#content-container',
                    'div#main-container',
                    'div#container',
                    'div#page',
                    'div#app',
                    'div#root',
                    'body',
                    'html'
                ];
                
                // Function to get text content with fallbacks
                const getText = (selector, context = document) => {
                    const el = context.querySelector(selector);
                    return el ? el.innerText.trim() : '';
                };
                
                // Try to find the main content container
                let mainContent = null;
                for (const selector of descriptionSelectors) {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        // Try to find the largest element with reasonable dimensions
                        const elementsArray = Array.from(elements);
                        elementsArray.sort((a, b) => {
                            const aSize = a.offsetWidth * a.offsetHeight;
                            const bSize = b.offsetWidth * b.offsetHeight;
                            return bSize - aSize;
                        });
                        
                        // Take the largest element that has some content
                        for (const el of elementsArray) {
                            if (el.innerText && el.innerText.trim().length > 100) {
                                mainContent = el;
                                break;
                            }
                        }
                        if (mainContent) break;
                    }
                }
                
                // If we found a main content area, use it
                if (mainContent) {
                    return {
                        full_description: mainContent.innerText.trim(),
                        html_content: mainContent.innerHTML,
                        found_using: mainContent.tagName.toLowerCase() + 
                                    (mainContent.id ? '#' + mainContent.id : '') + 
                                    (mainContent.className ? '.' + mainContent.className.replace(/\s+/g, '.') : '')
                    };
                }
                
                // Fallback to basic extraction
                return {
                    full_description: document.body.innerText,
                    html_content: document.documentElement.outerHTML,
                    found_using: 'fallback:document.body'
                };
            }""")
            
            # Combine all job info
            full_job_info = {
                **job,
                **job_details,
                scraped_at: datetime.utcnow().isoformat()
            }
            
            # Save the raw job details for debugging
            with open(f"job_{job.get('id', 'unknown')}.json", 'w', encoding='utf-8') as f:
                import json
                json.dump(full_job_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Successfully extracted job details. Title: {job.get('title', 'Unknown')}")
            
            # Generate cover letter (in a real app, this would call your LLM)
            cover_letter = await self.generate_cover_letter(full_job_info)
            
            # Save the generated cover letter
            with open(f"cover_letter_{job.get('id', 'unknown')}.txt", 'w', encoding='utf-8') as f:
                f.write(cover_letter)
            
            logger.info("\n" + "="*80)
            logger.info("GENERATED COVER LETTER:")
            logger.info("-"*80)
            logger.info(cover_letter)
            logger.info("="*80 + "\n")
            
            # Check if we can find the apply button (but don't click it)
            apply_button = await self.page.query_selector('button:has-text("Apply Now")')
            
            if not apply_button:
                logger.warning("Could not find 'Apply Now' button. The job may be filled or not open for applications.")
                # Try to find alternative apply button texts
                alternative_buttons = [
                    'Apply',
                    'Apply for this job',
                    'Apply now',
                    'Apply for position',
                    'Submit application',
                    'Apply with Indeed',
                    'Apply with LinkedIn',
                    'Quick apply',
                    'Apply for this position',
                    'Apply with resume'
                ]
                
                for btn_text in alternative_buttons:
                    alt_button = await self.page.query_selector(f'button:has-text("{btn_text}")')
                    if alt_button:
                        logger.info(f"Found alternative apply button: {btn_text}")
                        apply_button = alt_button
                        break
            
            if not apply_button:
                logger.warning("No apply button found. Here's the page structure for debugging:")
                # Log the page structure for debugging
                page_structure = await self.page.evaluate("""() => {
                    function getPath(element) {
                        if (!element || !element.tagName) return '';
                        const path = [];
                        while (element.nodeType === Node.ELEMENT_NODE) {
                            let selector = element.tagName.toLowerCase();
                            if (element.id) {
                                selector += '#' + element.id;
                                path.unshift(selector);
                                break;
                            } else {
                                let sib = element, nth = 1;
                                while (sib = sib.previousElementSibling) {
                                    if (sib.tagName.toLowerCase() === selector) nth++;
                                }
                                if (nth > 1) selector += ':nth-of-type(' + nth + ')';
                            }
                            path.unshift(selector);
                            element = element.parentNode;
                        }
                        return path.join(' > ');
                    }
                    
                    const buttons = [];
                    const allButtons = document.querySelectorAll('button, a[role="button"], input[type="button"], input[type="submit"]');
                    allButtons.forEach(btn => {
                        buttons.push({
                            text: btn.innerText.replace(/\s+/g, ' ').trim(),
                            tag: btn.tagName,
                            id: btn.id || '',
                            classes: btn.className || '',
                            path: getPath(btn)
                        });
                    });
                    return buttons;
                }""")
                
                logger.info("Page buttons:")
                for btn in page_structure:
                    if btn['text']:  # Only log buttons with text
                        logger.info(f"- {btn['text']} (tag: {btn['tag']}, id: {btn['id']}, classes: {btn['classes']})")
                        logger.info(f"  Selector: {btn['path']}")
            else:
                logger.info("Found apply button (not clicking in test mode)")
            
            # In test mode, we don't actually submit the application
            logger.info("TEST MODE: Application not submitted (test mode)")
            
            return {
                **full_job_info,
                status: "test_mode",
                success: True,
                cover_letter: cover_letter,
                applied_at: datetime.utcnow().isoformat(),
                test_mode: True
            }
            
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
                status: "error",
                success: False,
                error: str(e)
            }
    
    async def generate_cover_letter(self, job_info: Dict[str, Any]) -> str:
        """Generate a personalized cover letter for the job using job details"""
        logger.info("Generating cover letter...")
        
        try:
            # Extract key information from job details
            job_title = job_info.get('title', 'this position')
            company_name = job_info.get('company', 'your company')
            job_description = job_info.get('full_description', '')
            
            # Extract key requirements and responsibilities
            requirements = []
            responsibilities = []
            
            # Simple keyword extraction (in a real app, use NLP for better extraction)
            lines = job_description.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Look for requirement indicators
                req_indicators = ['requirement', 'qualification', 'skill', 'experience', 'proficiency', 'knowledge of', 'familiar with']
                if any(indicator in line.lower() for indicator in req_indicators):
                    requirements.append(line)
                
                # Look for responsibility indicators
                resp_indicators = ['responsibilit', 'dutie', 'you will', 'role will', 'key function']
                if any(indicator in line.lower() for indicator in resp_indicators):
                    responsibilities.append(line)
            
            # Limit the number of items for each section
            requirements = requirements[:5]  # Top 5 requirements
            responsibilities = responsibilities[:5]  # Top 5 responsibilities
            
            # Generate a personalized message
            cover_letter = f"""Dear Hiring Manager,

I'm excited to apply for the {job_title} position at {company_name}. With my background in [your field], I'm confident in my ability to contribute effectively to your team.

### Why I'm a Great Fit

I noticed that you're looking for someone with:
"""
            
            # Add requirements
            if requirements:
                for req in requirements:
                    cover_letter += f"- {req}\n"
            else:
                cover_letter += "- Strong problem-solving skills and a passion for technology\n"
                cover_letter += "- Ability to work in a fast-paced, collaborative environment\n"
            
            cover_letter += "\n### How I Can Add Value\n\n"
            
            # Add how you can help
            if responsibilities:
                for resp in responsibilities:
                    # Convert responsibility to first person
                    resp_text = resp.lower()
                    for pronoun in ['you will', 'the candidate will', 'they will']:
                        if pronoun in resp_text:
                            resp_text = resp_text.replace(pronoun, 'I can')
                    
                    # Capitalize first letter
                    if resp_text:
                        resp_text = resp_text[0].upper() + resp_text[1:]
                    
                    cover_letter += f"- {resp_text}\n"
            else:
                cover_letter += "- I'm eager to bring my skills in [relevant skills] to help [company_name] achieve [specific goal].\n"
                cover_letter += "- My experience with [relevant experience] aligns well with the challenges your team is tackling.\n"
            
            # Add a personal touch
            cover_letter += """
### Why [Company Name]

I'm particularly drawn to [specific aspect of company or role] because [specific reason]. I'm excited about the opportunity to [specific contribution] and help [specific impact].

I'd welcome the opportunity to discuss how my background and skills align with your needs. Thank you for your time and consideration.

Best regards,
[Your Name]"""
            
            # Replace placeholders
            cover_letter = cover_letter.replace('[your field]', 'software engineering')
            cover_letter = cover_letter.replace('[relevant skills]', 'Python, web development, and problem-solving')
            cover_letter = cover_letter.replace('[relevant experience]', 'building scalable applications')
            cover_letter = cover_letter.replace('[specific aspect of company or role]', f'the innovative work {company_name} is doing')
            cover_letter = cover_letter.replace('[specific reason]', 'I admire your commitment to [specific value or project]')
            cover_letter = cover_letter.replace('[specific contribution]', 'contribute to your team')
            cover_letter = cover_letter.replace('[specific impact]', 'drive meaningful results')
            
            return cover_letter
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {str(e)}")
            # Fallback to a simple template
            return f"""Dear Hiring Manager,

I'm excited to apply for the {job_info.get('title', 'position')} at {job_info.get('company', 'your company')}.

I believe my skills and experience make me a strong candidate for this role. I'm particularly drawn to {job_info.get('company', 'your company')} because of [specific reason].

Looking forward to the opportunity to discuss how I can contribute to your team.

Best regards,
[Your Name]"""

    async def run(self, email: str, password: str, max_applications: int = 5) -> Dict[str, Any]:
        """Run the complete automation workflow"""
        results = {
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

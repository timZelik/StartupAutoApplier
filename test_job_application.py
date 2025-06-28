#!/usr/bin/env python3
"""
Test script to run a single job application in test mode.
This will extract job details and generate a cover letter without submitting.
"""
import asyncio
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from automation.core import JobAutomator

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_application.log')
    ]
)

logger = logging.getLogger(__name__)

async def test_job_application(job_url: str):
    """Test the job application process for a single job"""
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    email = os.getenv("WORK_AT_A_STARTUP_EMAIL")
    password = os.getenv("WORK_AT_A_STARTUP_PASSWORD")
    
    if not email or not password:
        logger.error("Missing required environment variables. Please set WORK_AT_A_STARTUP_EMAIL and WORK_AT_A_STARTUP_PASSWORD in .env")
        sys.exit(1)
    
    # Create a test job object
    job = {
        "id": "test_job_123",
        "title": "Test Job",
        "company": "Test Company",
        "location": "Remote",
        "url": job_url,
        "description": "This is a test job description"
    }
    
    logger.info(f"Starting test job application for: {job_url}")
    
    # Run in non-headless mode so we can see what's happening
    async with JobAutomator(headless=False, slow_mo=100) as automator:
        try:
            # Login
            login_success = await automator.login(email, password)
            if not login_success:
                logger.error("Login failed")
                return
            
            # Process the job application (in test mode)
            result = await automator.process_job_application(job)
            
            # Save the results
            with open('test_application_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            
            logger.info("\n" + "="*80)
            logger.info("TEST COMPLETED SUCCESSFULLY")
            logger.info("="*80)
            logger.info(f"Job URL: {job_url}")
            logger.info(f"Cover letter saved to: cover_letter_{job.get('id', 'unknown')}.txt")
            logger.info(f"Job details saved to: job_{job.get('id', 'unknown')}.json")
            
            # Keep the browser open for inspection
            if os.getenv('KEEP_BROWSER_OPEN', 'false').lower() == 'true':
                logger.info("Keeping browser open for inspection (set KEEP_BROWSER_OPEN=false to disable)")
                await asyncio.sleep(3600)  # Keep open for 1 hour
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    # Get job URL from command line or use a default test URL
    if len(sys.argv) > 1:
        job_url = sys.argv[1]
    else:
        # Default to a test job URL (replace with a real one)
        job_url = "https://www.workatastartup.com/jobs/example-job-123"
        logger.warning(f"No job URL provided. Using test URL: {job_url}")
        logger.warning("To test with a real job, run: python test_job_application.py YOUR_JOB_URL")
    
    asyncio.run(test_job_application(job_url))

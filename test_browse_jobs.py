#!/usr/bin/env python3
"""
Test script to browse jobs on workatastartup.com and generate cover letters.
"""
import asyncio
import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add project root to path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from automation.core import JobAutomator, JobFilter

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('browse_jobs.log')
    ]
)

logger = logging.getLogger(__name__)

async def browse_jobs(max_jobs: int = 10) -> List[Dict[str, Any]]:
    """Browse jobs on workatastartup.com and return job listings"""
    logger.info("Starting job browser...")
    
    # Initialize the automator with headless=False to see the browser
    # and slow_mo to slow down the automation for better visibility
    automator = JobAutomator(headless=False, slow_mo=100)  # 100ms delay between actions
    
    try:
        # Set up the browser and page
        logger.info("Initializing browser...")
        await automator.setup()
        
        # Create a new page
        logger.info("Creating new page...")
        automator.page = await automator.context.new_page()
        
        # Load environment variables
        load_dotenv()
        
        # Get credentials
        email = os.getenv("WORK_AT_A_STARTUP_EMAIL")
        password = os.getenv("WORK_AT_A_STARTUP_PASSWORD")
        
        if not email or not password:
            logger.error("Missing required environment variables. Please set WORK_AT_A_STARTUP_EMAIL and WORK_AT_A_STARTUP_PASSWORD in .env")
            return []
        
        # Login
        logger.info("Logging in...")
        login_success = await automator.login(email, password)
        if not login_success:
            logger.error("Login failed")
            return []
        
        logger.info("Login successful!")
        
        # Add a small delay to see the result
        await asyncio.sleep(2)
        
        # Rest of your browsing logic will go here
        logger.info("Browsing jobs...")
        
        # Return empty list for now - we'll implement job listing retrieval next
        return []
        
    except Exception as e:
        logger.error(f"Error during browsing: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        # Make sure to close the browser when done
        logger.info("Closing browser...")
        await automator.close()
    
    # Run in non-headless mode so we can see what's happening
    async with JobAutomator(headless=False, slow_mo=100) as automator:
        try:
            # Login
            logger.info("Logging in...")
            login_success = await automator.login(email, password)
            if not login_success:
                logger.error("Login failed")
                return []
            
            # Apply filters
            logger.info("Applying filters...")
            job_filter = JobFilter()
            await automator.apply_filters(job_filter)
            
            # Get job listings
            logger.info(f"Fetching up to {max_jobs} job listings...")
            jobs = await automator.get_job_listings(max_listings=max_jobs)
            
            logger.info(f"\nFound {len(jobs)} jobs:")
            for i, job in enumerate(jobs, 1):
                print(f"{i}. {job.get('title', 'No title')} at {job.get('company', 'Unknown company')}")
                print(f"   {job.get('url')}")
                print()
            
            # Let user select a job
            while True:
                try:
                    selection = input(f"\nEnter a job number (1-{len(jobs)}) to generate a cover letter, or 'q' to quit: ")
                    if selection.lower() == 'q':
                        return []
                    
                    job_index = int(selection) - 1
                    if 0 <= job_index < len(jobs):
                        selected_job = jobs[job_index]
                        logger.info(f"\nSelected job: {selected_job.get('title')}")
                        
                        # Process the job application
                        result = await automator.process_job_application(selected_job)
                        
                        # Save the results
                        with open('job_application_result.json', 'w') as f:
                            json.dump(result, f, indent=2)
                        
                        # Display the cover letter
                        if 'cover_letter' in result:
                            print("\n" + "="*80)
                            print("GENERATED COVER LETTER:")
                            print("-"*80)
                            print(result['cover_letter'])
                            print("="*80 + "\n")
                        
                        # Ask if user wants to continue with another job
                        cont = input("Would you like to try another job? (y/n): ")
                        if cont.lower() != 'y':
                            break
                    else:
                        print(f"Please enter a number between 1 and {len(jobs)}")
                except ValueError:
                    print("Please enter a valid number or 'q' to quit")
            
            return jobs
            
        except Exception as e:
            logger.error(f"Error browsing jobs: {str(e)}", exc_info=True)
            return []

if __name__ == "__main__":
    # Run the job browser
    asyncio.run(browse_jobs(max_jobs=10))

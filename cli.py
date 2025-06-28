#!/usr/bin/env python3
"""
Command-line interface for the Job Automator
"""
import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from automation.core import JobAutomator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('automation.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the CLI"""
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    email = os.getenv("WORK_AT_A_STARTUP_EMAIL")
    password = os.getenv("WORK_AT_A_STARTUP_PASSWORD")
    
    if not email or not password:
        logger.error("Missing required environment variables. Please set WORK_AT_A_STARTUP_EMAIL and WORK_AT_A_STARTUP_PASSWORD in .env")
        sys.exit(1)
    
    # Get max applications (default: 5)
    try:
        max_applications = int(os.getenv("MAX_APPLICATIONS", "5"))
    except ValueError:
        max_applications = 5
    
    # Headless mode (default: False for local dev)
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    
    logger.info(f"Starting job automation (max applications: {max_applications}, headless: {headless})")
    
    try:
        # Run the automation
        async with JobAutomator(headless=headless) as automator:
            results = await automator.run(
                email=email,
                password=password,
                max_applications=max_applications
            )
            
            # Print results
            print("\n" + "="*50)
            print(f"Automation completed: {results['status']}")
            print(f"Total applications: {len(results['applications'])}")
            print(f"Successful: {results['success_count']}")
            print(f"Errors: {results['error_count']}")
            print("="*50 + "\n")
            
            # Log results
            logger.info(f"Automation completed: {results}")
            
    except Exception as e:
        logger.error(f"Automation failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

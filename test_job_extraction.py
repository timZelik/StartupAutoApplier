#!/usr/bin/env python3
"""
Test script to verify job extraction with the new HTML structure
"""
import asyncio
import json
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_job_extraction():
    """Test the job extraction functionality"""
    try:
        from automation.core import JobAutomator
        
        logger.info("🧪 Testing job extraction...")
        
        # Create automator instance
        async with JobAutomator(headless=True) as automator:
            # Navigate to the filtered page
            await automator.apply_filters(None)
            
            # Extract job listings
            jobs = await automator.get_job_listings(max_listings=5)
            
            logger.info(f"✅ Successfully extracted {len(jobs)} jobs")
            
            # Save the extracted data to a JSON file for inspection
            with open('extracted_jobs.json', 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=2, ensure_ascii=False)
            
            logger.info("📄 Saved extracted jobs to 'extracted_jobs.json'")
            
            # Print a sample job
            if jobs:
                sample_job = jobs[0]
                logger.info("📋 Sample job data:")
                logger.info(f"  Title: {sample_job.get('title', 'N/A')}")
                logger.info(f"  Company: {sample_job.get('company', {}).get('name', 'N/A')}")
                logger.info(f"  Location: {sample_job.get('location', 'N/A')}")
                logger.info(f"  Salary: {sample_job.get('salary', 'N/A')}")
                logger.info(f"  Equity: {sample_job.get('equity', 'N/A')}")
                logger.info(f"  URL: {sample_job.get('url', 'N/A')}")
                logger.info(f"  View Job URL: {sample_job.get('viewJobUrl', 'N/A')}")
                logger.info(f"  Has Apply Button: {sample_job.get('hasApplyButton', False)}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Job extraction test failed: {str(e)}")
        return False

async def main():
    """Run the test"""
    logger.info("🚀 Starting job extraction test...")
    
    success = await test_job_extraction()
    
    if success:
        logger.info("🎉 Job extraction test completed successfully!")
        logger.info("📁 Check 'extracted_jobs.json' for the full data structure")
    else:
        logger.error("❌ Job extraction test failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code) 
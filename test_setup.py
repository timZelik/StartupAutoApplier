#!/usr/bin/env python3
"""
Test script to verify the setup is working correctly
"""
import sys
import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_imports():
    """Test that all required modules can be imported"""
    logger.info("Testing imports...")
    
    try:
        from automation.core import JobAutomator
        logger.info("✅ JobAutomator imported successfully")
        
        from models.models import JobListing, Application, JobFilter
        logger.info("✅ Models imported successfully")
        
        from playwright.async_api import async_playwright
        logger.info("✅ Playwright imported successfully")
        
        return True
    except ImportError as e:
        logger.error(f"❌ Import failed: {e}")
        return False

async def test_playwright_setup():
    """Test that Playwright is properly installed"""
    logger.info("Testing Playwright setup...")
    
    try:
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            await browser.close()
        
        logger.info("✅ Playwright browser launched successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Playwright test failed: {e}")
        return False

async def test_environment():
    """Test environment configuration"""
    logger.info("Testing environment configuration...")
    
    try:
        from dotenv import load_dotenv
        import os
        
        load_dotenv()
        
        # Check if .env file exists
        if Path(".env").exists():
            logger.info("✅ .env file exists")
        else:
            logger.warning("⚠️  .env file not found")
        
        # Check if virtual environment is active
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            logger.info("✅ Virtual environment is active")
        else:
            logger.warning("⚠️  Virtual environment may not be active")
        
        return True
    except Exception as e:
        logger.error(f"❌ Environment test failed: {e}")
        return False

async def test_directory_structure():
    """Test that required directories exist"""
    logger.info("Testing directory structure...")
    
    required_dirs = ["videos", "logs"]
    missing_dirs = []
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            logger.info(f"✅ Directory '{dir_name}' exists")
        else:
            logger.warning(f"⚠️  Directory '{dir_name}' missing")
            missing_dirs.append(dir_name)
    
    return len(missing_dirs) == 0

async def main():
    """Run all tests"""
    logger.info("🧪 Running setup verification tests...")
    
    tests = [
        ("Imports", test_imports),
        ("Playwright Setup", test_playwright_setup),
        ("Environment", test_environment),
        ("Directory Structure", test_directory_structure)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("📊 Test Results Summary:")
    logger.info("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Setup is ready.")
        logger.info("\nNext steps:")
        logger.info("1. Edit .env file with your credentials")
        logger.info("2. Run: python cli.py")
        logger.info("3. Or use VS Code launch configurations")
    else:
        logger.error("❌ Some tests failed. Please check the setup.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 
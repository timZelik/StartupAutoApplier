#!/usr/bin/env python3
"""Test script to verify all imports are working correctly."""
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    print("Testing imports...")
    from automation.core import JobAutomator, JobFilter
    print("✅ Successfully imported automation.core")
    
    # Initialize JobAutomator
    print("\nInitializing JobAutomator...")
    automator = JobAutomator()
    print("✅ Successfully initialized JobAutomator")
    
    print("\n✅ All imports and initializations successful!")
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    print("\nPython path:")
    for p in sys.path:
        print(f"  - {p}")
    raise

#!/usr/bin/env python3
"""Simple script to check Python environment and imports."""
import sys
import os

def main():
    print("=" * 80)
    print("Python Environment Information")
    print("=" * 80)
    print(f"Python Version: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"\nPython Path:")
    for i, path in enumerate(sys.path):
        print(f"  {i+1:2d}. {path}")
    
    print("\nEnvironment Variables:")
    for key in sorted(os.environ.keys()):
        if 'PATH' in key or 'PYTHON' in key or 'VIRTUAL' in key:
            print(f"  {key} = {os.environ[key]}")
    
    print("\nTrying to import packages:")
    packages = ['playwright', 'pydantic', 'fastapi', 'uvicorn', 'python-dotenv', 'loguru']
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError as e:
            print(f"  ❌ {pkg}: {e}")

if __name__ == "__main__":
    main()

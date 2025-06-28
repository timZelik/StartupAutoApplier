#!/usr/bin/env python3
"""Check Python environment and package installation."""
import sys
import os
import subprocess

def run_command(cmd):
    print(f"\n$ {cmd}")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        print(result.stdout)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def main():
    print("=" * 80)
    print("Python Environment Check")
    print("=" * 80)
    
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    print(f"Virtual Env: {os.getenv('VIRTUAL_ENV', 'Not in a virtual environment')}")
    
    # Check if we're in a virtual environment
    if not os.getenv('VIRTUAL_ENV'):
        print("\n⚠️  Not running in a virtual environment. Please activate it first.")
        venv_path = os.path.join(os.path.dirname(__file__), 'venv')
        if os.path.exists(venv_path):
            print(f"\nTo activate the virtual environment, run:")
            print(f"  source {venv_path}/bin/activate")
        return
    
    # Check pip list
    print("\nInstalled packages:")
    run_command(f"{sys.executable} -m pip list")
    
    # Check playwright installation
    print("\nChecking Playwright installation:")
    run_command(f"{sys.executable} -m pip show playwright")
    
    # Try to import playwright
    print("\nTrying to import playwright:")
    try:
        import playwright
        print("✅ Successfully imported playwright")
        print(f"Playwright version: {playwright.__version__}")
    except ImportError as e:
        print(f"❌ Failed to import playwright: {e}")
    
    print("\n" + "=" * 80)
    print("Environment Check Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()

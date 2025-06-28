#!/usr/bin/env python3
"""Verify Python environment and Playwright installation."""
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
            capture_output=True,
            executable='/bin/zsh'  # Explicitly use zsh shell
        )
        print(result.stdout)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False, e.stderr

def main():
    print("=" * 80)
    print("Environment Verification")
    print("=" * 80)
    
    # Check Python version and path
    print(f"\nPython Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    print(f"Virtual Env: {os.getenv('VIRTUAL_ENV', 'Not in a virtual environment')}")
    
    # Check if we're in a virtual environment
    if not os.getenv('VIRTUAL_ENV'):
        print("\n⚠️  Not running in a virtual environment. Please activate it first.")
        venv_path = os.path.join(os.path.dirname(__file__), '.venv')
        if os.path.exists(venv_path):
            print(f"\nTo activate the virtual environment, run:")
            print(f"  source {venv_path}/bin/activate")
        return
    
    # Check pip list
    print("\nInstalled packages:")
    success, _ = run_command(f"{sys.executable} -m pip list")
    
    # Check playwright installation
    print("\nChecking Playwright installation:")
    success, _ = run_command(f"{sys.executable} -m pip show playwright")
    
    # Try to import playwright
    print("\nTrying to import playwright:")
    try:
        import playwright
        print("✅ Successfully imported playwright")
        print(f"Playwright version: {playwright.__version__}")
    except ImportError as e:
        print(f"❌ Failed to import playwright: {e}")
    
    # Check Python path
    print("\nPython path:")
    for i, path in enumerate(sys.path):
        print(f"  {i+1:2d}. {path}")
    
    # Check if we can run playwright
    print("\nTrying to run playwright --version:")
    run_command(f"{os.path.dirname(sys.executable)}/playwright --version")
    
    print("\n" + "=" * 80)
    print("Verification Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()

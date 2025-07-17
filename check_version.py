#!/usr/bin/env python3
import sys
import subprocess

print("Checking GestVenv installation...")
print("-" * 50)

# Test 1: Import direct
try:
    from gestvenv.__version__ import __version__
    print(f"✓ Direct import successful: {__version__}")
except Exception as e:
    print(f"✗ Direct import failed: {e}")

# Test 2: CLI module
try:
    result = subprocess.run([sys.executable, "-m", "gestvenv.cli", "--version"], 
                          capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ CLI module works: {result.stdout.strip()}")
    else:
        print(f"✗ CLI module failed: {result.stderr}")
except Exception as e:
    print(f"✗ CLI test failed: {e}")

# Test 3: Installed command
try:
    result = subprocess.run(["gv", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ 'gv' command works: {result.stdout.strip()}")
    else:
        print(f"✗ 'gv' command failed: {result.stderr}")
except Exception as e:
    print(f"✗ 'gv' command not found: {e}")

print("-" * 50)
print("Installation tip: pip install -e .")
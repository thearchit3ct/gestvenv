#!/usr/bin/env python3
"""Fix encoding issues in test files"""

import os
import re

def fix_encoding(file_path):
    """Fix encoding issues in a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try with latin-1 encoding
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Replace common French accented characters
    replacements = {
        'é': 'e',
        'è': 'e',
        'ê': 'e',
        'ë': 'e',
        'à': 'a',
        'â': 'a',
        'ä': 'a',
        'ç': 'c',
        'ù': 'u',
        'û': 'u',
        'ü': 'u',
        'ô': 'o',
        'ö': 'o',
        'î': 'i',
        'ï': 'i',
        'É': 'E',
        'È': 'E',
        'Ê': 'E',
        'Ë': 'E',
        'À': 'A',
        'Â': 'A',
        'Ä': 'A',
        'Ç': 'C',
        'Ù': 'U',
        'Û': 'U',
        'Ü': 'U',
        'Ô': 'O',
        'Ö': 'O',
        'Î': 'I',
        'Ï': 'I'
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Write back with UTF-8 encoding
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed encoding in {file_path}")

# Fix all performance test files
test_files = [
    "tests/performance/test_backend_performance.py",
    "tests/performance/test_cache_performance.py",
    "tests/performance/test_parsing_performance.py"
]

for file in test_files:
    if os.path.exists(file):
        fix_encoding(file)
#!/usr/bin/env python3
"""
Quick backend syntax test - run this locally before deploying!
"""
import sys
import os
import ast

print("🧪 Testing backend Python syntax...")

files_to_check = [
    'app/main.py',
    'app/routers/alerts.py',
    'app/routers/municipality.py',
    'app/services/postgres_service.py',
]

all_ok = True
for filepath in files_to_check:
    try:
        with open(filepath, 'r') as f:
            ast.parse(f.read())
        print(f"  ✓ {filepath}")
    except SyntaxError as e:
        print(f"  ❌ {filepath}: {e}")
        all_ok = False

if all_ok:
    print("\n✅ All files have valid Python syntax! Safe to deploy.")
    sys.exit(0)
else:
    print("\n❌ Syntax errors found! Fix before deploying.")
    sys.exit(1)

#!/usr/bin/env python3
"""
Syntax and encoding scanner for Python files.
Scans all .py files in the workspace for syntax errors and invalid characters.
"""

import ast
import os
import sys
from pathlib import Path

def scan_file(filepath):
    """Scan a single Python file for syntax and encoding issues."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='strict') as f:
            content = f.read()
        
        # Check for invalid characters (non-printable except common whitespace)
        for i, char in enumerate(content):
            if not (char.isprintable() or char in '\n\t\r'):
                line_num = content[:i].count('\n') + 1
                col_num = i - content.rfind('\n', 0, i) if '\n' in content[:i] else i + 1
                print(f"SYNTAX ERROR: {filepath}:{line_num}:{col_num} -> invalid character '{char}' (U+{ord(char):04X})")
                return True
        
        # Try to parse the AST
        ast.parse(content, filename=filepath)
        return False
    except SyntaxError as e:
        print(f"SYNTAX ERROR: {filepath}:{e.lineno}:{e.offset} -> {e.msg}")
        return True
    except UnicodeDecodeError as e:
        print(f"ENCODING ERROR: {filepath} -> {e}")
        return True
    except Exception as e:
        print(f"ERROR scanning {filepath}: {e}")
        return True

def main():
    """Main function to scan all Python files."""
    workspace_root = Path.cwd()
    python_files = []
    
    # Find all .py files
    for root, dirs, files in os.walk(workspace_root):
        # Skip common directories
        dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', '.venv', 'node_modules', '.vscode'}]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    
    print(f"Scanning {len(python_files)} Python files...")
    
    errors_found = 0
    for filepath in sorted(python_files):
        if scan_file(filepath):
            errors_found += 1
    
    print(f"\nFiles scanned: {len(python_files)}, errors: {errors_found}")
    
    if errors_found > 0:
        sys.exit(1)
    else:
        print("✓ All files passed syntax and encoding checks!")

if __name__ == "__main__":
    main()
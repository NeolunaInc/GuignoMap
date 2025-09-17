#!/usr/bin/env python3
"""
GuignoMap Structure Validation Script
=====================================

Validates the project structure for:
- No circular imports
- UTF-8 encoding
- No hardcoded paths
- Single database layer

Usage:
    python scripts/validate_structure.py
"""

import os
import sys
import ast
import chardet
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
import importlib.util


class StructureValidator:
    """Validates GuignoMap project structure and coding standards."""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.errors = []
        self.warnings = []
        
    def log_error(self, message: str):
        """Log a validation error."""
        self.errors.append(f"❌ ERROR: {message}")
        
    def log_warning(self, message: str):
        """Log a validation warning."""
        self.warnings.append(f"⚠️  WARNING: {message}")
        
    def log_info(self, message: str):
        """Log an info message."""
        print(f"ℹ️  {message}")

    def get_python_files(self) -> List[Path]:
        """Get all Python files in the project, excluding certain directories."""
        exclude_dirs = {'.venv', '__pycache__', '.git', 'node_modules', 'backups'}
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories from traversal
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
                    
        return python_files

    def no_circular_imports(self) -> bool:
        """Check for circular imports in Python files."""
        self.log_info("Checking for circular imports...")
        
        python_files = self.get_python_files()
        imports_graph = {}
        
        # Build import graph
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=str(py_file))
                
                module_path = str(py_file.relative_to(self.project_root)).replace('\\', '/').replace('.py', '').replace('/', '.')
                imports_graph[module_path] = set()
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports_graph[module_path].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports_graph[module_path].add(node.module)
                            
            except Exception as e:
                self.log_warning(f"Could not parse {py_file}: {e}")
                continue
        
        # Check for cycles using DFS
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in imports_graph.get(node, set()):
                if neighbor in imports_graph:  # Only check internal modules
                    if neighbor not in visited:
                        if has_cycle(neighbor, visited, rec_stack):
                            return True
                    elif neighbor in rec_stack:
                        self.log_error(f"Circular import detected: {node} -> {neighbor}")
                        return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        has_cycles = False
        
        for module in imports_graph:
            if module not in visited:
                if has_cycle(module, visited, set()):
                    has_cycles = True
        
        if not has_cycles:
            self.log_info("✅ No circular imports found")
            
        return not has_cycles

    def utf8_encoding(self) -> bool:
        """Check that all Python files are UTF-8 encoded."""
        self.log_info("Checking UTF-8 encoding...")
        
        python_files = self.get_python_files()
        all_utf8 = True
        
        for py_file in python_files:
            try:
                with open(py_file, 'rb') as f:
                    raw_data = f.read()
                    
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', '') if result else ''
                encoding = encoding.lower() if encoding else 'unknown'
                
                if encoding not in ['utf-8', 'ascii', 'utf-8-sig'] and encoding != 'unknown':
                    self.log_error(f"File {py_file} is not UTF-8 encoded (detected: {encoding})")
                    all_utf8 = False
                    
            except Exception as e:
                self.log_warning(f"Could not check encoding of {py_file}: {e}")
                
        if all_utf8:
            self.log_info("✅ All Python files are UTF-8 encoded")
            
        return all_utf8

    def no_hardcoded_paths(self) -> bool:
        """Check for hardcoded paths in Python files."""
        self.log_info("Checking for hardcoded paths...")
        
        python_files = self.get_python_files()
        hardcoded_patterns = [
            r'["\']C:\\',  # Windows absolute paths
            r'["\'][A-Za-z]:\\',  # Drive letters
            r'["\']\/home\/',  # Linux home paths
            r'["\']\/usr\/',   # Linux system paths
            r'["\']\/var\/',   # Linux var paths
        ]
        
        # Compile patterns
        compiled_patterns = [re.compile(pattern) for pattern in hardcoded_patterns]
        has_hardcoded = False
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for i, line in enumerate(content.split('\n'), 1):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue
                        
                    for pattern in compiled_patterns:
                        if pattern.search(line):
                            self.log_error(f"Hardcoded path in {py_file}:{i}: {line.strip()}")
                            has_hardcoded = True
                            
            except Exception as e:
                self.log_warning(f"Could not check {py_file}: {e}")
                
        if not has_hardcoded:
            self.log_info("✅ No hardcoded paths found")
            
        return not has_hardcoded

    def single_db_layer(self) -> bool:
        """Check that database layer is unified (no db_v5 imports, operations.py exists)."""
        self.log_info("Checking single database layer...")
        
        # Check that operations.py exists
        operations_file = self.project_root / 'src' / 'database' / 'operations.py'
        if not operations_file.exists():
            self.log_error("src/database/operations.py does not exist")
            return False
            
        # Check for any remaining db_v5 imports in active code
        python_files = self.get_python_files()
        db_v5_imports = False
        
        for py_file in python_files:
            # Skip the compatibility shim
            if py_file.name == 'db_v5.py':
                continue
                
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for actual import statements (not comments)
                for i, line in enumerate(content.split('\n'), 1):
                    line_stripped = line.strip()
                    # Skip comments and docstrings
                    if line_stripped.startswith('#') or line_stripped.startswith('"""') or line_stripped.startswith("'''"):
                        continue
                        
                    if 'db_v5' in line and ('import' in line or 'from' in line):
                        # Make sure it's not in a string or comment - but exclude this validation file
                        if str(py_file).endswith('validate_structure.py'):
                            continue
                        if re.search(r'(^|[^#]*)import.*db_v5|from.*db_v5.*import', line):
                            self.log_error(f"Found db_v5 import in {py_file}:{i}: {line.strip()}")
                            db_v5_imports = True
                            
            except Exception as e:
                self.log_warning(f"Could not check {py_file}: {e}")
        
        # Check that main imports use operations
        app_py = self.project_root / 'guignomap' / 'app.py'
        if app_py.exists():
            try:
                with open(app_py, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'from src.database import operations' not in content:
                        self.log_warning("app.py should import from src.database.operations")
            except Exception as e:
                self.log_warning(f"Could not check app.py: {e}")
        
        if not db_v5_imports:
            self.log_info("✅ Single database layer confirmed (no db_v5 imports found)")
            
        return not db_v5_imports

    def validate_project(self) -> bool:
        """Run all validations and return overall result."""
        print("🔍 GuignoMap Structure Validation")
        print("=" * 50)
        
        results = []
        
        # Run all validation checks
        results.append(self.no_circular_imports())
        results.append(self.utf8_encoding())
        results.append(self.no_hardcoded_paths())
        results.append(self.single_db_layer())
        
        print("\n" + "=" * 50)
        print("📋 VALIDATION REPORT")
        print("=" * 50)
        
        # Print warnings
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   {warning}")
        
        # Print errors
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"   {error}")
        
        # Overall result
        all_passed = all(results) and not self.errors
        
        print(f"\n🎯 OVERALL RESULT: {'✅ PASSED' if all_passed else '❌ FAILED'}")
        
        if all_passed:
            print("   All validations passed! Project structure is clean.")
        else:
            print(f"   {len(self.errors)} error(s) found. Please fix before proceeding.")
            
        return all_passed


def main():
    """Main entry point."""
    validator = StructureValidator()
    success = validator.validate_project()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
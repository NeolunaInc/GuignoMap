#!/usr/bin/env python3
"""
Fix mojibake (corrupted text due to encoding issues) in text files using ftfy.

Usage:
    python scripts/fix_mojibake_files.py [--paths file1 file2 ...] [--apply]
    
Options:
    --paths: Specific file paths to process (space-separated)
    --apply: Actually write changes (default is DRY-RUN mode)
    
Examples:
    # DRY-RUN on specific files
    python scripts/fix_mojibake_files.py --paths guignomap/app.py docs/README.md
    
    # Apply changes to specific files
    python scripts/fix_mojibake_files.py --apply --paths guignomap/app.py docs/README.md
    
    # DRY-RUN on all files in repo
    python scripts/fix_mojibake_files.py
    
    # Apply changes to all files in repo
    python scripts/fix_mojibake_files.py --apply
"""

import argparse
import difflib
import os
import sys
from pathlib import Path
from typing import List, Set

try:
    import ftfy
except ImportError:
    print("Error: ftfy library not found. Install with: pip install ftfy")
    sys.exit(1)


# Exclusions
EXCLUDED_DIRS = {'.git', '.venv', '__pycache__', 'node_modules', '.pytest_cache'}
EXCLUDED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.zip', '.sqlite', '.db', '.xlsx', '.xls', '.ico', '.pyc', '.pyo'}

# Target extensions for text files
TARGET_EXTENSIONS = {'.py', '.md', '.txt', '.json', '.toml', '.csv', '.yml', '.yaml', '.ini', '.cfg', '.conf'}

# Emoji replacements for correcting corrupted emojis (applied after ftfy)
EMOJI_REPLACEMENTS = {
    "ÔøΩ": "🧾",
    "üëî": "👤",
    "üîê": "🔑",
    "üöÄ": "🔓",
    "üéÖ": "🎄",
    "üìû": "📞",
    "üö∂": "⏳",
    "üë•": "👥",
    "üìù": "📝",
    "üåü": "🏆",
    "üì±": "📄",
    "üéâ": "🎉",
    "üìç": "📌",
    "üìä": "📊",
    "üõ†": "🛠️",
    "üíæ": "🗃️",
    "üìã": "✅",
    "üì§": "📤",
    "üì•": "📊",  # Export icon
    "üö®": "ℹ️",  # Info icon
    "üîç": "🔧",  # Tools icon
    "'úÖ": "✅",  # Success icon
    "'ùå": "❌",  # Error icon
    "■": "",      # Remove square boxes
    "□": ""       # Remove empty squares
}


def is_excluded_path(path: Path) -> bool:
    """Check if path should be excluded from processing."""
    # Skip files in excluded directories
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return True
    
    # Skip files with excluded extensions
    if path.suffix.lower() in EXCLUDED_EXTENSIONS:
        return True
    
    # Skip exports directory for binary/data files
    if 'exports' in path.parts and path.suffix.lower() in {'.csv', '.txt'}:
        # Allow some exports but be careful with data files
        if any(name in path.name.lower() for name in ['export_', 'sanity_', 'streets_template']):
            return True
    
    return False


def should_process_file(path: Path) -> bool:
    """Check if file should be processed (is a target text file)."""
    if is_excluded_path(path):
        return False
    
    # Only process files with target extensions
    if path.suffix.lower() not in TARGET_EXTENSIONS:
        return False
    
    # Must be a regular file
    if not path.is_file():
        return False
    
    return True


def get_files_to_process(base_path: Path, specific_paths: List[str] | None = None) -> List[Path]:
    """Get list of files to process."""
    files = []
    
    if specific_paths:
        # Process specific files
        for path_str in specific_paths:
            path = base_path / path_str
            if path.exists() and path.is_file():
                if should_process_file(path):
                    files.append(path)
                else:
                    print(f"Warning: Skipping excluded file: {path}")
            else:
                print(f"Warning: File not found: {path}")
    else:
        # Process all files recursively
        for root, dirs, filenames in os.walk(base_path):
            # Remove excluded directories from dirs list to skip them
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            
            for filename in filenames:
                path = Path(root) / filename
                if should_process_file(path):
                    files.append(path)
    
    return sorted(files)


def fix_file_mojibake(file_path: Path, dry_run: bool = True) -> tuple[bool, str, str, str]:
    """
    Fix mojibake in a single file using ftfy and custom emoji replacements.
    
    Returns:
        (has_changes, original_content, fixed_content, diff_summary)
    """
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            original_content = f.read()
        
        # Fix mojibake using ftfy
        fixed_content = ftfy.fix_text(original_content)
        
        # Apply emoji replacements for .py, .md, .txt files
        if file_path.suffix.lower() in {'.py', '.md', '.txt'}:
            for corrupted, correct in EMOJI_REPLACEMENTS.items():
                fixed_content = fixed_content.replace(corrupted, correct)
        
        # Check if there are changes
        has_changes = original_content != fixed_content
        
        if not has_changes:
            return False, original_content, fixed_content, "No changes needed"
        
        # Generate diff summary
        diff_lines = list(difflib.unified_diff(
            original_content.splitlines(keepends=True),
            fixed_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=2
        ))
        
        # Count changed lines
        changed_lines = sum(1 for line in diff_lines if line.startswith('+') or line.startswith('-'))
        diff_summary = f"{changed_lines} lines changed"
        
        # If not dry run, write the file
        if not dry_run:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(fixed_content)
        
        return has_changes, original_content, fixed_content, diff_summary
        
    except Exception as e:
        return False, "", "", f"Error: {e}"


def show_diff_preview(original: str, fixed: str, max_lines: int = 10) -> str:
    """Show a preview of the diff."""
    diff_lines = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        fixed.splitlines(keepends=True),
        fromfile="original",
        tofile="fixed",
        n=2
    ))
    
    if len(diff_lines) <= max_lines:
        return ''.join(diff_lines)
    else:
        preview = diff_lines[:max_lines]
        preview.append(f"... ({len(diff_lines) - max_lines} more lines)\n")
        return ''.join(preview)


def main():
    parser = argparse.ArgumentParser(description='Fix mojibake in text files using ftfy')
    parser.add_argument('--apply', action='store_true', 
                       help='Actually apply changes (default is DRY-RUN)')
    parser.add_argument('--paths', nargs='*', 
                       help='Specific file paths to process (relative to repo root)')
    parser.add_argument('--show-diff', action='store_true',
                       help='Show diff preview for files with changes')
    
    args = parser.parse_args()
    
    # Get repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    print(f"Processing files in: {repo_root}")
    print(f"Mode: {'APPLY CHANGES' if args.apply else 'DRY-RUN (no changes written)'}")
    print()
    
    # Get files to process
    files_to_process = get_files_to_process(repo_root, args.paths)
    
    if not files_to_process:
        print("No files to process.")
        return
    
    print(f"Found {len(files_to_process)} files to process:")
    for file_path in files_to_process:
        rel_path = file_path.relative_to(repo_root)
        print(f"  {rel_path}")
    print()
    
    # Process files
    changed_files = []
    error_files = []
    
    for file_path in files_to_process:
        rel_path = file_path.relative_to(repo_root)
        print(f"Processing: {rel_path}")
        
        has_changes, original, fixed, summary = fix_file_mojibake(file_path, dry_run=not args.apply)
        
        if "Error:" in summary:
            print(f"  ❌ {summary}")
            error_files.append(rel_path)
        elif has_changes:
            print(f"  ✅ {summary}")
            changed_files.append(rel_path)
            
            if args.show_diff:
                print("  Diff preview:")
                diff_preview = show_diff_preview(original, fixed)
                for line in diff_preview.splitlines():
                    print(f"    {line}")
                print()
        else:
            print(f"  ✅ {summary}")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Files processed: {len(files_to_process)}")
    print(f"Files with changes: {len(changed_files)}")
    print(f"Files with errors: {len(error_files)}")
    
    if changed_files:
        print()
        print("Files with changes:")
        for file_path in changed_files:
            status = "APPLIED" if args.apply else "WOULD CHANGE"
            print(f"  {status}: {file_path}")
    
    if error_files:
        print()
        print("Files with errors:")
        for file_path in error_files:
            print(f"  ERROR: {file_path}")
    
    if not args.apply and changed_files:
        print()
        print("To apply these changes, run with --apply flag:")
        if args.paths:
            paths_str = ' '.join(f'"{p}"' for p in args.paths)
            print(f"  python scripts/fix_mojibake_files.py --apply --paths {paths_str}")
        else:
            print("  python scripts/fix_mojibake_files.py --apply")


if __name__ == '__main__':
    main()
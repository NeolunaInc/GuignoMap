# [GM] BEGIN cleanup_workspace.py
from __future__ import annotations
import argparse, os, re, sys, shutil
from pathlib import Path

VOLATILE_PATTERNS = [
    re.compile(r'^status_counts_.*\.csv$'),
    re.compile(r'^unassigned_.*\.csv$'),
    re.compile(r'^sanity_.*\.csv$'),
]
VOLATILE_REPORTS = [
    re.compile(r'^export.*\.txt$'),
    re.compile(r'^GuignoMap_code_export_.*\.txt$'),
    re.compile(r'^pylance_errors_report_.*\.txt$'),
]

def rm(path: Path, apply: bool):
    if path.exists():
        if apply:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                try: path.unlink()
                except: pass
        print(f"{'DEL' if apply else 'DRY'} {path}")

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='apply deletion')
    p.add_argument('--keep-days', type=int, default=7)
    args = p.parse_args(argv)

    # caches
    for d in (Path('.pytest_cache'), Path('.ruff_cache')):
        rm(d, args.apply)

    # exports volatils
    exp = Path('exports')
    if exp.exists():
        for f in exp.glob('*'):
            if any(pat.match(f.name) for pat in VOLATILE_PATTERNS):
                rm(f, args.apply)

    # rapports ponctuels à la racine
    root = Path('.')
    for f in root.glob('*'):
        if f.is_file() and any(pat.match(f.name) for pat in VOLATILE_REPORTS):
            rm(f, args.apply)

    # backups vieux (sauf DB active)
    b = Path('backups')
    if b.exists():
        import datetime
        now = datetime.datetime.now()
        for f in b.rglob('*'):
            if f.is_file():
                age = (now - datetime.datetime.fromtimestamp(f.stat().st_mtime)).days
                if age >= args.keep_days:
                    rm(f, args.apply)

    # legacy : notifier seulement
    if Path('legacy').exists():
        print("INFO legacy/ détecté. Supprimez-le via CLEAN-4 si validé.")

if __name__ == "__main__":
    sys.exit(main())
# [GM] END cleanup_workspace.py
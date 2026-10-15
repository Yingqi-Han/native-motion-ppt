#!/usr/bin/env python3
"""Refresh a completed run's portable sources/report and reverify its archive."""
import argparse
import json
from pathlib import Path
from accept_project import finalize_run

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("run")
    parser.add_argument("--visual-review-note",help="Only use after viewing this run's native frames; cannot clear target/Morph pending states")
    parser.add_argument('--review-file',help='Structured review containing current recording hashes, check IDs, notes and in-run evidence paths')
    args=parser.parse_args()
    print(finalize_run(args.run,args.visual_review_note,json.loads(Path(args.review_file).read_text()) if args.review_file else None))

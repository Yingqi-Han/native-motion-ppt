#!/usr/bin/env python3
"""Render and verify an already generated Remotion design project."""
import argparse
import sys
from pathlib import Path
from build_demo import render_design

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder");parser.add_argument("--out",required=True)
    args=parser.parse_args()
    result=render_design(Path(args.folder).resolve(),"project",sys.executable,0,Path(args.out).resolve(),False)
    print(result)

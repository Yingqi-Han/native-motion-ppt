#!/usr/bin/env python3
"""Suggest motion timing from source geometry without changing the project."""
import argparse,json
from native_motion.model import load
from native_motion.motion_advice import advise
from native_motion.acceptance import save
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('spec');p.add_argument('--out',required=True);a=p.parse_args()
 d=advise(load(a.spec));save(a.out,d);print(json.dumps(d,ensure_ascii=False,indent=2))

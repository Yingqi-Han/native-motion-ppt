#!/usr/bin/env python3
"""Report task-specific readiness and repair commands, without installing anything."""
import argparse
from native_motion.readiness import collect, print_report, STAGES


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-player', choices=['impress-desktop', 'wps-desktop', 'powerpoint-desktop'])
    parser.add_argument('--desktop-tools-root')
    parser.add_argument('--wps-root')
    parser.add_argument('--wps-profile')
    parser.add_argument('--spec')
    parser.add_argument('--for', dest='stage', choices=STAGES)
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--text', action='store_true', help='Human-readable output; default remains JSON')
    args = parser.parse_args(argv)
    report = collect(args.target_player, args.desktop_tools_root, args.wps_root, args.wps_profile, args.spec)
    print_report(report, args.stage, as_json=not args.text)
    if args.strict and args.stage and report['stages'][args.stage]['status'] != 'passed':
        return 2
    if args.strict and report.get('selected_desktop_backend', {}).get('status') == 'pending':
        return 2
    return 0 if report['core_pptx'] else 1


if __name__ == '__main__':
    raise SystemExit(main())


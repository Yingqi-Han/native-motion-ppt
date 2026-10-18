"""Resolve the same real Chromium executable for design sampling and rendering."""
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


def browser_path():
    explicit = os.environ.get('NMP_BROWSER_EXECUTABLE')
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file() or (os.name != 'nt' and not os.access(path, os.X_OK)):
            raise ValueError('NMP_BROWSER_EXECUTABLE is not an executable file: ' + str(path))
        return str(path)
    for name in ('chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable'):
        found = shutil.which(name)
        if found:
            return found
    try:
        if importlib.util.find_spec('playwright'):
            probe = subprocess.run(
                [sys.executable, '-c', 'from playwright.sync_api import sync_playwright\nwith sync_playwright() as p: print(p.chromium.executable_path)'],
                capture_output=True, text=True, timeout=10,
            )
            path = Path(probe.stdout.strip())
            if probe.returncode == 0 and path.is_file():
                return str(path)
    except (ImportError, OSError, subprocess.SubprocessError):
        pass
    return None

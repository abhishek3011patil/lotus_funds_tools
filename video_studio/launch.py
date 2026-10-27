"""Start a loopback-only local studio, reusing an existing instance."""
import json
import os
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
if (ROOT / '.runtime' / 'browsers').exists():
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / '.runtime' / 'browsers')
URL = 'http://127.0.0.1:8765'

def is_running():
    try:
        with urllib.request.urlopen(URL + '/api/health', timeout=1) as response:
            return json.load(response).get('app') == 'tarkash-video-studio'
    except Exception:
        return False

def show_when_ready():
    for _ in range(120):
        if is_running():
            webbrowser.open(URL)
            return
        time.sleep(.5)

if __name__ == '__main__':
    if is_running():
        webbrowser.open(URL)
    else:
        threading.Thread(target=show_when_ready, daemon=True).start()
        import uvicorn
        uvicorn.run('app:app', host='127.0.0.1', port=8765, log_level='info')

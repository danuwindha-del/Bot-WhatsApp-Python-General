"""Full browser regression suite. Requires Playwright and Chromium, no AI key."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

os.chdir(Path(__file__).resolve().parents[2])
with tempfile.TemporaryFile() as logs:
    process = subprocess.Popen([sys.executable, 'tests/ui/server.py'], stdout=logs, stderr=subprocess.STDOUT)
    try:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError('Demo server exited before readiness; free port 8765 first.')
            try:
                urllib.request.urlopen('http://127.0.0.1:8765/healthz', timeout=.2)
                break
            except Exception:
                time.sleep(.05)
        else:
            raise RuntimeError('Demo server did not start')
        result = subprocess.run(['node', 'tests/ui/browser.cjs'])
        sys.exit(result.returncode)
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        logs.seek(0)
        print(logs.read().decode()[-2000:])

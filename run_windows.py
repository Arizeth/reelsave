"""Local Windows launcher. No administrator privileges or activation required."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent
ADDRESS = 'http://127.0.0.1:8000'


def open_when_ready():
    for _ in range(60):
        try:
            with urllib.request.urlopen(ADDRESS, timeout=1) as response:
                if response.status == 200 and b'ReelSave' in response.read(65536):
                    webbrowser.open(ADDRESS)
                    return
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.5)
    print('Browser did not open. Check the server output, then open ' + ADDRESS)


def main():
    if os.name != 'nt':
        raise SystemExit('This launcher is for Windows. See README.md for Linux instructions.')
    os.chdir(ROOT)
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise SystemExit('FFmpeg and ffprobe must be on PATH. Restart VS Code after updating PATH.')
    python = ROOT / '.venv' / 'Scripts' / 'python.exe'
    if not python.exists():
        print('Creating project virtual environment...', flush=True)
        venv.create(ROOT / '.venv', with_pip=True)
    if Path(sys.executable).resolve() != python.resolve():
        result = subprocess.run([str(python), str(Path(__file__).resolve())])
        raise SystemExit(result.returncode)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')], check=True)
    # Refuse to open a different service if port 8000 is already occupied.
    import socket
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', 8000))
        except OSError:
            raise SystemExit('Port 8000 is already in use. Stop the previous server and try again.')
    print('Starting ReelSave. Keep this window open. Press Ctrl+C to stop.', flush=True)
    threading.Thread(target=open_when_ready, daemon=True).start()
    import uvicorn
    uvicorn.run('app:app', host='127.0.0.1', port=8000, workers=1, proxy_headers=False)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f'Setup command failed (exit {exc.returncode}). Check the output above.')

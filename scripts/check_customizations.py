"""Run the fork's portable regression checks. Requires NumPy and Requests."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
main = root / 'game/controllers/MainSupervisor'
tests = sorted((root / 'tests').glob('test_*.py'))
for test in tests:
    target = root if test.name == 'test_cross_platform.py' else main
    print(f"Running {test.name}", flush=True)
    subprocess.run([sys.executable, str(test), str(target)], cwd=root, check=True)
print(f"PASS: {len(tests)} regression scripts")

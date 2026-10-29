"""Prepare an ignored default robot model before the first Webots launch."""
# Checkout preparation by Peyman Yousefi.
from pathlib import Path
from shutil import copyfile

root = Path(__file__).resolve().parents[1]
target = root / 'game/protos/custom_robot.proto'
if target.exists():
    print('Existing robot model preserved.')
else:
    copyfile(root / 'game/proto_defaults/E-puck-custom-default-FLU.proto', target)
    print('Initial robot model prepared. Load your custom robot JSON before Run.')

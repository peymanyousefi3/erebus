"""First-checkout setup must never overwrite a participant's robot model."""
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess,sys,shutil
root=Path(__file__).resolve().parents[1]
with TemporaryDirectory() as temp:
    copy=Path(temp)
    (copy/'scripts').mkdir();(copy/'game/protos').mkdir(parents=True);(copy/'game/proto_defaults').mkdir()
    shutil.copyfile(root/'scripts/prepare_world.py',copy/'scripts/prepare_world.py')
    (copy/'game/proto_defaults/E-puck-custom-default-FLU.proto').write_text('default')
    subprocess.run([sys.executable,str(copy/'scripts/prepare_world.py')],check=True,capture_output=True)
    model=copy/'game/protos/custom_robot.proto';assert model.read_text()=='default'
    model.write_text('participant model')
    subprocess.run([sys.executable,str(copy/'scripts/prepare_world.py')],check=True,capture_output=True)
    assert model.read_text()=='participant model'
print('PASS: fresh checkout model prepared; existing robot model preserved.')

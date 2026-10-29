"""Regression checks for file retention and JSON error handling; no Webots needed."""
import ast
import glob
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS


root = Path(sys.argv[1]).resolve()
sys.path.insert(0,str(root))
import ControllerUploader


def method(file, cls, name, namespace):
    tree = ast.parse((root / file).read_text())
    body = next(n.body for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls)
    node = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), file, 'exec'), namespace)
    return namespace[name]


messages = []
namespace = dict(json=json, Console=NS(log_err=lambda text: None))
load = method('MainSupervisor.py', 'Erebus', '_process_robot_json', namespace)
supervisor = NS(rws=NS(send=lambda *args: messages.append(args)))
namespace['generate_robot_proto'] = lambda data: True
for invalid in ['{broken', '[]', 'null']:
    load(supervisor, invalid)
    assert messages[-1][0] == 'sourceFileError'
namespace['generate_robot_proto'] = lambda data: False
load(supervisor, '{}')
assert messages[-1][0] == 'sourceFileError'
namespace['generate_robot_proto'] = lambda data: True
load(supervisor, '{}')
assert messages[-1] == ('loaded1',)

with TemporaryDirectory() as temp:
    module = Path(temp) / 'controllers/MainSupervisor/Controller.py'
    module.parent.mkdir(parents=True)
    runtime = module.parent.parent / 'robot0Controller'
    runtime.mkdir()
    (runtime / '__pycache__').mkdir()
    namespace = dict(ControllerUploader=ControllerUploader,os=os, glob=glob, __file__=str(module))
    reset = method('Controller.py', 'Controller', 'reset_file', namespace)
    controller = NS(keep_controller=True, _erebus=supervisor)
    placeholder = runtime / 'robot0Controller.py'
    placeholder.write_text('')
    messages.clear()
    reset(controller)
    assert not messages, 'Empty placeholder/cache must not look like a loaded controller'
    placeholder.write_text('print("retained")\n')
    reset(controller)
    assert messages == [('loaded0',)]

print('PASS: malformed JSON is recoverable; saved empty placeholders are not marked loaded.')

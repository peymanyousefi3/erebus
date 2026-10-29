"""Check removal of OS-specific additions and compatibility of old settings."""
from pathlib import Path
import ast,sys
from urllib.parse import unquote
root=Path(sys.argv[1]).resolve()
main=root/'game/controllers/MainSupervisor'
ui=root/'game/plugins/robot_windows/MainSupervisorWindow'
for name in ('SourcePicker.m','source-picker-macos'):
 assert not (main/name).exists(),name
for p in [main/name for name in ('MainSupervisor.py','Config.py','Recorder.py','MatchAnimation.py','ControllerUploader.py')]+[ui/'MainSupervisorWindow.js',ui/'MainSupervisorWindow.html']:
 text=p.read_text()
 for token in ('AppKit','source-picker','sys.platform','navigator.platform','showOpenFilePicker','/Users/','/Applications/'):
  assert token not in text,(p.name,token)
html=(ui/'MainSupervisorWindow.html').read_text()
assert all(token in html for token in ('autoReloadSources','controllerSource'))
assert 'jsonSource' not in html
import re
assert 'checked' not in re.search(r'<input[^>]*id="autoReloadSources"[^>]*>',html)[0]
assert 'type="file"' in html and 'showHud' in html and 'autoRemoveFiles' in html
namespace={'unquote':unquote,'Console':type('Console',(),{'update_debug_mode':staticmethod(lambda flag:None)})}
cls=next(n for n in ast.parse((main/'Config.py').read_text()).body if isinstance(n,ast.ClassDef))
exec(compile(ast.Module(body=[cls],type_ignores=[]),'<Config>','exec'),namespace)
for data in (['1','0','0','0','0','0',''],['1','0','0','0','0','0','','1','C:%5Cold%5Cfile.py','/old/mac/robot.json','0']):
 config=namespace['Config'](data,'config.txt')
 assert config.auto_reload_sources==(len(data)>7 and data[7]=='1')
 assert config.show_hud==(len(data)<=10 or data[10]!='0')
print('PASS: browser picker only; no OS-specific added helpers or paths; manual reload defaults off without a native helper; HUD/Keep retained. This is not a Windows/Linux runtime test.')

"""Run a local Mac controller with only its own files and the public robot port.

Requires the controller-only gateway and a private organizer Webots backend.
Unrestricted native Run remains a development mode, not competition isolation.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import site
import tempfile


def profile(code, work, sdk, port):
    quote=lambda p:json.dumps(str(p),ensure_ascii=False)
    reads=[code, sdk, Path(sys.base_prefix), Path(sys.executable).resolve().parent,
           Path(sysconfig.get_path('stdlib')),Path(sysconfig.get_path('purelib')),Path(site.getusersitepackages())]
    reads += list(map(Path,('/System/Library','/System/Applications','/System/Cryptexes','/System/Volumes/Preboot','/usr/bin','/usr/lib','/usr/sbin','/usr/share','/bin','/sbin','/Library/Frameworks','/Library/Apple','/opt/homebrew/bin','/opt/homebrew/lib','/opt/homebrew/Cellar','/usr/local/bin','/usr/local/lib','/usr/local/opt','/usr/local/Cellar','/private/etc','/private/var/db/dyld','/private/preboot','/private/var/db/oah')))
    protected=Path(__file__).resolve().parents[1]
    paths=' '.join('(subpath '+quote(p.resolve())+')' for p in reads)
    return f'''(version 1)
(deny default)
(allow process*)
(allow signal (target self))
(allow sysctl-read)
(allow file-read-metadata)
(allow file-read* (literal "/"))
(allow file-read* (require-all (require-any {paths}) (require-not (subpath {quote(protected)}))))
(allow file-read* (subpath {quote(code)}) (subpath {quote(work)}))
(allow file-write* (subpath {quote(work)}) (literal "/dev/null"))
(allow file-read* (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random"))
(allow network-outbound (remote tcp "localhost:{port}"))
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('program',type=Path)
    p.add_argument('--webots-home',type=Path,default=Path('/Applications/Webots 2.app'))
    p.add_argument('--port',type=int,default=1234)
    a=p.parse_args()
    if sys.platform!='darwin' or not Path('/usr/bin/sandbox-exec').is_file():
        p.error('This launcher requires the Mac sandbox; use the isolated Docker participant on other systems.')
    if not 1<=a.port<=65535:p.error('Invalid controller gateway port.')
    program=a.program.resolve(strict=True);sdk=a.webots_home.resolve(strict=True)
    launcher=sdk/'Contents/MacOS/webots-controller'
    if not launcher.is_file():p.error('Webots controller launcher was not found.')
    # Copy only the installed controller directory, never the Erebus project.
    if any((program.parent/name).exists() for name in ('game','worlds','protos','MainSupervisor')):
        p.error('Use a dedicated controller directory, without organizer files.')
    base=Path(__file__).resolve().parents[1]/'validation/restricted-controllers';base.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base) as temp:
        temp=Path(temp).resolve();code=temp/'code';work=temp/'work';work.mkdir()
        if any(path.is_file() and path.stat().st_nlink > 1 for path in program.parent.rglob('*') if not path.is_symlink()):
            p.error('Controller dependencies must not be hard links to host files.')
        shutil.copytree(program.parent,code,symlinks=True)
        if any(path.is_symlink() for path in code.rglob('*')):
            p.error('Controller dependencies must be real files, not links to host files.')
        policy=temp/'controller.sb';policy.write_text(profile(code,work,sdk,a.port))
        env={key:value for key,value in os.environ.items() if key in ('PATH','LANG','LC_ALL')}
        env.update(WEBOTS_HOME=str(sdk),TMPDIR=str(work)+'/',PYTHONDONTWRITEBYTECODE='1')
        command=['/usr/bin/sandbox-exec','-f',str(policy),str(launcher),'--protocol=tcp','--ip-address=127.0.0.1','--port='+str(a.port),'--robot-name=Erebus_Bot',str(code/program.name)]
        return subprocess.call(command,cwd=work,env=env)


if __name__=='__main__':
    raise SystemExit(main())

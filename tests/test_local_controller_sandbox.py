"""Mac OS enforcement, independent of a visible simulator window."""
import asyncio,importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
if sys.platform!='darwin':
    print('SKIP: Mac sandbox enforcement is exercised on macOS; Docker isolation is checked separately.')
    raise SystemExit(0)
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,root/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
local=module('local','scripts/run_restricted_controller.py');gateway=module('gateway','scripts/controller_gateway.py')
async def run():
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp).resolve();code=temp/'code';work=temp/'work';code.mkdir();work.mkdir()
        secret=temp/'organizer-answer.txt';secret.write_text('hidden map and victim data')
        async def backend(reader,writer):
            try:
                await reader.readexactly(len(b'CTR\nRobot-Name: Erebus_Bot'))
                writer.write(b'CONNECTED');await writer.drain();await gateway.relay(reader,writer)
            finally:writer.close()
        private=await asyncio.start_server(backend,'127.0.0.1',0);private_port=private.sockets[0].getsockname()[1]
        public=await asyncio.start_server(lambda r,w:gateway.controller(r,w,'127.0.0.1',private_port,'Erebus_Bot'),'127.0.0.1',0);port=public.sockets[0].getsockname()[1]
        try:
            policy=temp/'policy.sb';policy.write_text(local.profile(code,work,Path('/Applications/Webots 2.app'),port))
            script=f'''
from pathlib import Path
import socket,struct
try: Path({str(secret)!r}).read_text()
except PermissionError: pass
else: raise AssertionError('Private organizer file was readable')
alias=Path('/System/Volumes/Data')/Path({str(secret)!r}).relative_to('/')
try: alias.read_text()
except (PermissionError,FileNotFoundError): pass
else: raise AssertionError('Organizer data was readable through the Data volume alias')
link=Path('answer-link');link.symlink_to({str(secret)!r})
try: link.read_text()
except PermissionError: pass
else: raise AssertionError('Organizer data was readable through a controller symlink')

try: socket.create_connection(('127.0.0.1',{private_port}),timeout=1)
except PermissionError: pass
else: raise AssertionError('Private backend was reachable')
s=socket.create_connection(('127.0.0.1',{port}),timeout=2)
s.sendall(b'CTR\\nRobot-Name: Erebus_Bot');assert s.recv(9)==b'CONNECTED'
payload=struct.pack('<I',21)+b'legal robot bytes'
s.sendall(payload);assert s.recv(100)==payload;s.close()
Path('controller-output.txt').write_text('allowed output')
print('PASS: Mac controller cannot read organizer files or contact private Webots; allowed robot traffic and own output work.')
'''
            command=['/usr/bin/sandbox-exec','-f',str(policy),sys.executable,'-c',script]
            result=await asyncio.to_thread(subprocess.run,command,cwd=work,capture_output=True,text=True,timeout=20)
            assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
            assert (work/'controller-output.txt').read_text()=='allowed output'
            print(result.stdout.strip())
        finally:
            public.close();private.close();await public.wait_closed();await private.wait_closed()
asyncio.run(run())

"""Exercise real authenticated HTTP routes and a real upstream WebSocket tunnel."""
from pathlib import Path
from datetime import datetime, timezone
import base64
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'game/controllers/MainSupervisor'))
from AccessAudit import AccessAudit
from AccessMonitor import AccessMonitor
from RefereeService import RefereeService, RefereeConnections


def get(url, data=None, headers=None, method=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(url,data=data,headers=headers or {},method=method),timeout=3) as response:
            return response.status,response.read(),response.headers
    except urllib.error.HTTPError as response:
        return response.code,response.read(),response.headers


with tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary);assets=root/'game/plugins/robot_windows/MainSupervisorWindow';assets.mkdir(parents=True)
    (assets/'MainSupervisorWindow.html').write_text('<html><head></head><body>Controls</body></html>')
    (assets/'thumbnails').mkdir();(assets/'thumbnails/field.png').write_bytes(b'preview bytes')
    report=root/'match-results/test/map.html';report.parent.mkdir(parents=True);report.write_text('private map')
    (root/'outside.html').write_text('must stay private')
    audit=AccessAudit(root);audit.start();connections=RefereeConnections()
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1]
    peers=[]
    def backend():
        client,peer=listener.accept();peers.append(peer)
        with client:
            data=b''
            while b'\r\n\r\n' not in data:data+=client.recv(4096)
            assert b'GET / HTTP/1.1' in data
            client.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n')
            data=client.recv(4096);client.sendall(data)
    server_thread=threading.Thread(target=backend,daemon=True);server_thread.start()
    service=RefereeService(root,port,connections,audit);service.start(open_browser=False)
    try:
        status,body,headers=get(service.url)
        assert status==200 and b'window.erebusReferee=' in body
        assert headers['Referrer-Policy']=='no-referrer' and headers['Cache-Control']=='no-store'
        base=service.origin+service.prefix
        assert get(base+'robot_windows/MainSupervisorWindow/thumbnails/field.png')[1]==b'preview bytes'
        assert get(base+'reports/test/map.html')[1]==b'private map'
        assert get(base+'reports/../../outside.html')[0]==404
        assert get(base+'reports/%2e%2e/%2e%2e/outside.html')[0]==404
        assert get(service.origin+'/favicon.ico')[0]==204
        assert get(service.origin+'/apple-touch-icon.png')[0]==204
        assert audit.snapshot()[1]['warnings']==0,'Normal referee activity caused an alert'
        status,_,_=get(base+'commands',b'run',{'Content-Type':'text/plain'})
        assert status==202 and list(service.receive_commands())==['run']
        assert get(service.origin+'/wrong/commands',b'reset',{'User-Agent':'referee browser'})[0]==403
        assert get(base+'commands',b'reset',{'Origin':'https://untrusted.example'})[0]==403
        assert not list(service.receive_commands()),'Unauthorised command was queued'
        assert get(base+'commands',b'',{'Content-Length':str(service.MAX_COMMAND+1)})[0]==413
        assert audit.snapshot()[1]['warnings']==2
        with socket.create_connection(('127.0.0.1',service._server.server_port),3) as client:
            client.settimeout(3)
            key=base64.b64encode(os.urandom(16)).decode()
            client.sendall(('GET '+service.prefix+' HTTP/1.1\r\nHost: '+service.authority+'\r\nOrigin: '+service.origin+'\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: '+key+'\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
            assert client.recv(4096).startswith(b'HTTP/1.1 101 ')
            stamp=time.time();peer=peers[0]
            assert connections.authorised(peer[0],peer[1],'127.0.0.1',port,stamp)
            iso_stamp=datetime.fromtimestamp(stamp,timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')+'000Z'
            assert connections.authorised(peer[0],peer[1],'127.0.0.1',port,iso_stamp)
            assert not connections.authorised(peer[0],peer[1]+1,'127.0.0.1',port,stamp),'An entire IP was trusted'
            monitor=AccessMonitor(root,referee_connections=connections);monitor._prepare_directory();monitor.port=port
            fields={'frame.number':'1','frame.time_epoch':str(stamp),'tcp.stream':'1','ip.src':peer[0],
                'tcp.srcport':str(peer[1]),'ip.dst':'127.0.0.1','tcp.dstport':str(port),
                'http.request.method':'GET','http.request.uri':'/','http.upgrade':'websocket'}
            monitor._http(fields)
            assert not monitor.snapshot()[1]['events'][0]['warning']
            monitor._http(dict(fields,**{'frame.number':'2','tcp.stream':'2','tcp.srcport':str(peer[1]+1)}))
            assert monitor.snapshot()[1]['events'][-1]['warning'],'Same-IP direct connection escaped detection'
            client.sendall(b'raw frame bytes');assert client.recv(4096)==b'raw frame bytes'
        server_thread.join(timeout=3)
        time.sleep(.05)
        assert not connections.authorised(peer[0],peer[1],'127.0.0.1',port,time.time()+1),'A reused source port stayed trusted'
        assert service.token not in json.dumps(audit.snapshot()[1]),'Session credential leaked into broadcast audit'
    finally:
        service.close();audit.close();listener.close()
print('PASS: authenticated previews/reports/commands without alerts; bad credentials/origins/traversal rejected; real WebSocket tunnel; exact-flow classification and no blanket IP trust.')

# The production receive gate must never execute direct Webots window commands.
import ast
from types import SimpleNamespace
from typing import Optional
source=Path(__file__).resolve().parents[1]/'game/controllers/MainSupervisor/MainSupervisor.py'
klass=next(node for node in ast.parse(source.read_text()).body if isinstance(node,ast.ClassDef) and node.name=='Erebus')
update=next(node for node in klass.body if isinstance(node,ast.FunctionDef) and node.name=='update')
index=next(index for index,node in enumerate(update.body) if isinstance(node,ast.For) and 'receive_commands' in ast.unparse(node.iter))
function=ast.FunctionDef(name='receive_gate',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg='self')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=update.body[index:index+3],decorator_list=[])
module=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]));scope={'Optional':Optional};exec(compile(module,'<actual referee receive gate>','exec'),scope)
executed=[];rejected=[];untrusted=iter(['reset','config,forged',None])
supervisor=SimpleNamespace(referee_service=SimpleNamespace(receive_commands=lambda:iter(['run','showMapReview'])),
 _process_rw_message=executed.append,wwiReceiveText=lambda:next(untrusted),access_audit=SimpleNamespace(record=lambda *args,**kwargs:rejected.append((args,kwargs))))
scope['receive_gate'](supervisor)
assert executed==['run','showMapReview'] and len(rejected)==2
assert all(event[1]['warning'] for event in rejected)
print('PASS: actual supervisor receive gate executes authenticated controls and rejects direct reset/config commands.')

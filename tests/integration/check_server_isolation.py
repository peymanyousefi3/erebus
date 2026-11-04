"""Real Webots deployment: organizer preview works; participant network cannot read it."""
from pathlib import Path
import json,os,subprocess,sys,time,urllib.request,urllib.error
root=Path(__file__).resolve().parents[2]
compose=['docker','compose','-p','erebus-map-isolation','-f',str(root/'docker/competition/compose.yaml')]
out=root/'validation/server-isolation';out.mkdir(parents=True,exist_ok=True)
def run(args,**kwargs):return subprocess.run(args,check=True,text=True,**kwargs)
try:
    version=run(['docker','version','--format','{{.Server.Version}}'],capture_output=True).stdout.strip()
    assert int(version.split('.')[0])>=28,'Docker Engine 28+ is required for private loopback bindings'
    run(compose+['up','--build','-d','webots','gateway'])
    forwarding=run(compose+['exec','-T','gateway','cat','/proc/sys/net/ipv4/ip_forward'],capture_output=True).stdout.strip()
    assert forwarding=='0','Gateway must not route participant packets into the organizer network'
    url='http://127.0.0.1:1240/robot_windows/MainSupervisorWindow/thumbnails/mapping_example_1_cyan_tiles.png?check=1'
    deadline=time.monotonic()+180
    while True:
        try:
            with urllib.request.urlopen(url,timeout=3) as response:
                data=response.read();assert response.status==200 and data.startswith(b'\x89PNG')
            break
        except OSError:
            state=run(compose+['ps','--all','--format','json'],capture_output=True).stdout
            if 'exited' in state.lower():raise AssertionError('A server container exited: '+state)
            if time.monotonic()>deadline:raise
            time.sleep(1)
    backend=run(compose+['ps','-q','webots'],capture_output=True).stdout.strip()
    details=json.loads(run(['docker','inspect',backend],capture_output=True).stdout)[0]
    private_ip=next(iter(details['NetworkSettings']['Networks'].values()))['IPAddress']
    # The organizer can still read the field, while even its upload service
    # refuses downloads. This is the exact file-service leak in the original.
    field=json.loads(run(compose+['exec','-T','webots','python3','-c',
        "from pathlib import Path;import hashlib,json; p=Path('/erebus/game/worlds/mapping_example_1_cyan_tiles.wbt'); b=p.read_bytes(); assert b'Victim {' in b; c=Path('/erebus/game/controllers/MainSupervisor/config.txt').read_text().split(','); assert c[5]=='0'; test=Path('/erebus/match-results/.write-check'); test.write_text('organizer'); test.unlink(); print(json.dumps(dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),debug_enabled=False,results_writable=True)))"],capture_output=True).stdout)
    paths=['/worlds/','/worlds/world1.wbt','/worlds/mapping_example_1_cyan_tiles.wbt',
        '/worlds/mapping_example_1_cyan_tiles.wbt?download=1','/protos/Victim.proto',
        '/controllers/MainSupervisor/Victim.py','/controllers/MainSupervisor/sensorEnergyConfig.txt',
        '/worlds/textures/victim_harmed_not_found.png','/%2e%2e/worlds/world1.wbt',
        '/robot_windows/MainSupervisorWindow/thumbnails/mapping_example_1_cyan_tiles.png',
        '/robot_windows/MainSupervisorWindow/MainSupervisorWindow.html','/']
    upload_checks=[]
    for method in ('GET','HEAD'):
        for path in paths:
            deadline=time.monotonic()+30
            while True:
                try:
                    urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:60520'+path,method=method),timeout=3)
                except urllib.error.HTTPError as error:
                    assert error.code==403,(method,path,error.code)
                    upload_checks.append(dict(method=method,path=path,status=error.code));break
                except OSError:
                    if time.monotonic()>deadline:raise
                    time.sleep(.5)
                else:raise AssertionError(('Uploader disclosed organizer data',method,path))
    network='erebus-map-isolation_participants'
    # The same download attempts run as a plain remote client and from inside
    # the actual participant SDK container, before normal robot exchanges.
    def download_probe(host):
        return f'''import socket,json
checks=[]
for method in ('GET','HEAD'):
 for path in {paths!r}:
  with socket.create_connection(({host!r},1234),timeout=3) as s:
   s.settimeout(3);s.sendall((method+' '+path+' HTTP/1.1\\r\\nHost: server\\r\\n\\r\\n').encode())
   try: data=s.recv(4096)
   except ConnectionResetError: data=b''
   assert data==b'',(method,path,data[:100])
   checks.append(dict(method=method,path=path,bytes_received=len(data)))
print('DOWNLOAD_CHECKS='+json.dumps(checks),flush=True)
'''
    host_probe=run([sys.executable,'-c',download_probe('127.0.0.1')],capture_output=True)
    remote_checks=json.loads(host_probe.stdout.split('DOWNLOAD_CHECKS=')[1].splitlines()[0])
    attack=f'''
import socket,urllib.request,json
from pathlib import Path
assert not Path('/erebus/game').exists() and not Path('/var/run/docker.sock').exists()
blocked=[]
for host,port in [({private_ip!r},1255),({private_ip!r},60520),('host.docker.internal',1240),('host.docker.internal',60520)]:
 try: s=socket.create_connection((host,port),timeout=2)
 except OSError: blocked.append(dict(host=host,port=port))
 else: s.close();raise AssertionError(('Organizer endpoint reachable',host,port))
print('PRIVATE_ENDPOINTS='+json.dumps(blocked),flush=True)
'''+download_probe('gateway')
    attacker=run(['docker','run','--rm','--network',network,'--add-host','host.docker.internal:host-gateway','python:3.12-slim','python','-c',attack],capture_output=True)
    private_checks=json.loads(attacker.stdout.split('PRIVATE_ENDPOINTS=')[1].splitlines()[0])
    docker_checks=json.loads(attacker.stdout.split('DOWNLOAD_CHECKS=')[1].splitlines()[0])
    # Organizer-only WWI still controls the real supervisor.
    session=''
    for _ in range(60):
        credential=subprocess.run(compose+['exec','-T','webots','cat','/tmp/erebus-referee.cfg'],capture_output=True,text=True)
        if credential.returncode==0:
            session=credential.stdout.strip();break
        time.sleep(1)
    assert session,'Authenticated organizer service did not start'
    js="""const page=require('node:fs').readFileSync(0,'utf8').trim();const url=new URL(page);const prefix=url.pathname.slice(0,url.pathname.indexOf('/robot_windows/')+1);
const socket=new WebSocket('ws://'+url.host+prefix);let sent=false;
const timeout=setTimeout(()=>{console.error('Authenticated organizer operation timed out');process.exit(1)},30000);
socket.onopen=async()=>{socket.send('robot:robot:init robot window');const response=await fetch(url.origin+prefix+'commands',{method:'POST',body:process.argv[1]});if(response.status!==202)process.exit(1)};
socket.onmessage=e=>{const marker=process.argv[1]==='run'?'runPressed':'mapReviewSaved,';if(e.data.includes(marker)){clearTimeout(timeout);socket.close()}};
socket.onerror=()=>process.exit(1);
"""
    run(['node','-e',js,'run'],input=session)
    controller=out/'robot_controller.py'
    controller.write_text(download_probe('gateway')+'''from controller import Supervisor\nimport struct,json\nr=Supervisor();assert not r.getSupervisor();assert not r.getRoot()._ref;assert r.getFromDef('MAINSUPERVISOR') is None;e=r.getDevice('emitter');rx=r.getDevice('receiver');rx.enable(16)\nfor name in ('wheel1 motor','wheel2 motor'):\n m=r.getDevice(name);m.setPosition(float('inf'));m.setVelocity(3.14)\nfor _ in range(70):assert r.step(16)!=-1\ne.send(struct.pack('2i',3,3)+b'0,0,0,0,5,0,0,0,0')\nfor _ in range(4):r.step(16)\ne.send(b'M');e.send(b'G')\ninfo=None\nfor _ in range(50):\n r.step(16)\n while rx.getQueueLength():\n  data=rx.getBytes()\n  if len(data)==20:info=struct.unpack('c f i i f',data)\n  rx.nextPacket()\nassert info and info[0]==b'G' and 0<info[4]<100\nprint('PASS: real external robot motion, map submission/evaluation, game-info and battery reply through public gateway.',flush=True)\ne.send(b'E')\nfor _ in range(10):\n if r.step(16)==-1:break\n''')
    sdk=run(['docker','run','--rm','--network',network,'--mount',f'type=bind,src={controller},dst=/controller/robot_controller.py,readonly','--entrypoint','/usr/local/webots/webots-controller','cyberbotics/webots:R2025a-ubuntu22.04','--protocol=tcp','--ip-address=gateway','--port=1234','--robot-name=Erebus_Bot','/controller/robot_controller.py'],capture_output=True)
    (out/'participant.log').write_text(sdk.stdout+sdk.stderr)
    sdk_checks=json.loads(sdk.stdout.split('DOWNLOAD_CHECKS=')[1].splitlines()[0])
    assert 'PASS: real external robot motion' in sdk.stdout
    # The organizer's map-review command and automatic replay must both export
    # into the private results volume without requiring container root access.
    run(['node','-e',js,'showMapReview'],input=session)
    exports=json.loads(run(compose+['exec','-T','webots','python3','-c',
        "from pathlib import Path;import json; root=Path('/erebus/match-results'); matches=list(root.rglob('match-result.json')); maps=list(root.rglob('map-result.json')); archives=list(root.rglob('*.zip')); assert len(matches)==len(maps)==len(archives)==1; assert list(root.rglob('replay.html')) and list(root.rglob('map-review.html')); result=json.loads(matches[0].read_text()); print(json.dumps(dict(replay=True,map_review=True,archive=True,final_score=result['final_score'])))"],capture_output=True).stdout)
    logs=run(compose+['logs','--no-color'],capture_output=True).stdout
    assert '[EREBUS ERROR]' not in logs,logs
    with urllib.request.urlopen(url,timeout=3) as response:
        assert response.status==200 and response.read().startswith(b'\x89PNG')
    (out/'result.json').write_text(json.dumps(dict(passed=True,organizer_preview=True,participant_preview=False,private_backend=False,real_robot_protocol=True,organizer_world=field,organizer_exports=exports,uploader_downloads=upload_checks,remote_downloads=remote_checks,docker_downloads=docker_checks,sdk_controller_downloads=sdk_checks,private_endpoints=private_checks),indent=2))
finally:
    with (out/'containers.log').open('w') as log:subprocess.run(compose+['logs','--no-color'],stdout=log,stderr=subprocess.STDOUT,text=True)
    subprocess.run(compose+['down','--volumes'],check=False)

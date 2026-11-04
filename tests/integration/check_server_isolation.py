"""Real Webots deployment: organizer preview works; participant network cannot read it."""
from pathlib import Path
import json,os,subprocess,time,urllib.request
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
    network='erebus-map-isolation_participants'
    attack=f'''
import socket,urllib.request
from pathlib import Path
assert not Path('/erebus/game').exists() and not Path('/var/run/docker.sock').exists()
for host,port in [({private_ip!r},1255),('host.docker.internal',1240),('host.docker.internal',60520)]:
 try: s=socket.create_connection((host,port),timeout=2)
 except OSError: pass
 else: s.close();raise AssertionError(('Organizer endpoint reachable',host,port))
for path in ['/robot_windows/MainSupervisorWindow/thumbnails/mapping_example_1_cyan_tiles.png','/robot_windows/MainSupervisorWindow/MainSupervisorWindow.html','/']:
 s=socket.create_connection(('gateway',1234),timeout=2)
 s.sendall(('GET '+path+' HTTP/1.1\\r\\nHost: gateway\\r\\n\\r\\n').encode())
 try: data=s.recv(100)
 except ConnectionResetError: data=b''
 assert not data;s.close()
print('PASS: controller network cannot access previews, private Webots, organizer uploads or organizer files.')
'''
    run(['docker','run','--rm','--network',network,'--add-host','host.docker.internal:host-gateway','python:3.12-slim','python','-c',attack])
    # Organizer-only WWI still controls the real supervisor.
    js="""const socket=new WebSocket('ws://127.0.0.1:1240/');let started=false;let retry;
const timeout=setTimeout(()=>{console.error('Organizer interface did not start match');process.exit(1)},30000);
socket.onopen=()=>{socket.send('robot:robot:init robot window');socket.send('robot:robot:rw_reload');retry=setInterval(()=>socket.send('robot:robot:rw_reload'),500)};
socket.onmessage=e=>{if(!started && (e.data.includes('startup')||e.data.includes('config,'))){started=true;clearInterval(retry);socket.send('robot:robot:remoteDisable');socket.send('robot:robot:run')};if(e.data.includes('runPressed')){clearTimeout(timeout);clearInterval(retry);socket.close()}};
socket.onerror=e=>{console.error(e);process.exit(1)};
"""
    run(['node','--input-type=module','-e',js])
    controller=out/'robot_controller.py'
    controller.write_text('''from controller import Supervisor\nimport struct,json\nr=Supervisor();assert not r.getSupervisor();assert not r.getRoot()._ref;assert r.getFromDef('MAINSUPERVISOR') is None;e=r.getDevice('emitter');rx=r.getDevice('receiver');rx.enable(16)\nfor name in ('wheel1 motor','wheel2 motor'):\n m=r.getDevice(name);m.setPosition(float('inf'));m.setVelocity(3.14)\nfor _ in range(70):assert r.step(16)!=-1\ne.send(struct.pack('2i',3,3)+b'0,0,0,0,5,0,0,0,0')\nfor _ in range(4):r.step(16)\ne.send(b'M');e.send(b'G')\ninfo=None\nfor _ in range(50):\n r.step(16)\n while rx.getQueueLength():\n  data=rx.getBytes()\n  if len(data)==20:info=struct.unpack('c f i i f',data)\n  rx.nextPacket()\nassert info and info[0]==b'G' and 0<info[4]<100\nprint('PASS: real external robot motion, map submission/evaluation, game-info and battery reply through public gateway.',flush=True)\ne.send(b'E')\nfor _ in range(10):\n if r.step(16)==-1:break\n''')
    run(['docker','run','--rm','--network',network,'--mount',f'type=bind,src={controller},dst=/controller/robot_controller.py,readonly','--entrypoint','/usr/local/webots/webots-controller','cyberbotics/webots:R2025a-ubuntu22.04','--protocol=tcp','--ip-address=gateway','--port=1234','--robot-name=Erebus_Bot','/controller/robot_controller.py'])
    (out/'result.json').write_text(json.dumps(dict(passed=True,organizer_preview=True,participant_preview=False,private_backend=False,real_robot_protocol=True),indent=2))
finally:
    with (out/'containers.log').open('w') as log:subprocess.run(compose+['logs','--no-color'],stdout=log,stderr=subprocess.STDOUT,text=True)
    subprocess.run(compose+['down','--volumes'],check=False)

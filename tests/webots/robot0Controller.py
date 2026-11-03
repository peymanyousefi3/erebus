"""Exercise the real controller API and emitter/receiver packet path."""
from controller import Robot,Node
from pathlib import Path
import json,struct,math,hashlib
r=Robot();root=Path(__file__).resolve().parents[3]
devices=[r.getDeviceByIndex(i) for i in range(r.getNumberOfDevices())]
wheels=[d for d in devices if d.getNodeType()==Node.ROTATIONAL_MOTOR]
for d in wheels:d.setPosition(float('inf'));d.setVelocity(3.14)
sensors=[d for d in devices if d.getNodeType() in (Node.CAMERA,Node.LIDAR,Node.GPS,Node.GYRO,Node.ACCELEROMETER,Node.INERTIAL_UNIT,Node.DISTANCE_SENSOR,Node.POSITION_SENSOR)]
for d in sensors:d.enable(16)
info=[]
for d in devices:
    entry=dict(name=d.getName(),type=type(d).__name__)
    if d.getNodeType()==Node.CAMERA:entry.update(width=d.getWidth(),height=d.getHeight())
    info.append(entry)
(root/'device-info.json').write_text(json.dumps(info))
r.setCustomData('0,0')
e=r.getDevice('emitter');receiver=r.getDevice('receiver');receiver.enable(16)
requested=False;last='';imaging_disabled=False
while r.step(16)!=-1:
    text=r.getCustomData()
    if text in ('stop','run'):
        for w in wheels:w.setVelocity(0 if text=='stop' else 6.28)
        # Images were sampled before these command-driven timing checks.
        if not imaging_disabled:
            for device in sensors:
                if device.getNodeType() in (Node.CAMERA,Node.LIDAR):device.disable()
            imaging_disabled=True
    elif text.startswith('{') and text!=last:
        last=text;cmd=json.loads(text)
        if 'report' in cmd:
            x,z,kind=cmd['report'];e.send(struct.pack('i i c',round(x*100),round(z*100),kind.encode()))
        if cmd.get('map'):
            matrix=json.loads((root/'expected-map.json').read_text());e.send(struct.pack('2i',len(matrix),len(matrix[0]))+','.join(v for row in matrix for v in row).encode())
        if cmd.get('evaluate'):e.send(b'M')
        if cmd.get('exit'):e.send(b'E')
    if not requested and r.getTime()>.3:
        for d in sensors:
            item=next(v for v in info if v['name']==d.getName())
            if d.getNodeType()==Node.CAMERA:
                frame=d.getImage();assert frame and len(frame)==4*d.getWidth()*d.getHeight()
                item.update(image_bytes=len(frame),image_sha256=hashlib.sha256(frame).hexdigest())
            elif d.getNodeType()==Node.LIDAR:
                ranges=d.getRangeImage();assert len(ranges)==d.getHorizontalResolution()*d.getNumberOfLayers()
                item.update(range_samples=len(ranges),finite_samples=sum(math.isfinite(v) for v in ranges))
            elif d.getNodeType()==Node.INERTIAL_UNIT:assert all(math.isfinite(v) for v in d.getRollPitchYaw())
            elif d.getNodeType() in (Node.GPS,Node.GYRO,Node.ACCELEROMETER):assert all(math.isfinite(v) for v in d.getValues())
            else:assert math.isfinite(d.getValue())
        (root/'device-info.json').write_text(json.dumps(info))
        print('EREBUS_TEST_DEVICES '+json.dumps(info),flush=True)
        e.send(b'G');requested=True
    while receiver.getQueueLength():
        packet=receiver.getBytes()
        if len(packet)==20:
            kind,score,sim,real,battery=struct.unpack('c f i i f',packet)
            payload=dict(kind=kind.decode(),score=score,simulation_remaining=sim,real_remaining=real,battery=battery)
            (root/'game-info.json').write_text(json.dumps(payload))
            print('EREBUS_TEST_GAME_INFO '+json.dumps(payload),flush=True)
        receiver.nextPacket()

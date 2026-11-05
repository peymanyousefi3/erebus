"""Sensor-driven endurance entrant; no scene handles, supplied map or pose commands."""
from controller import Robot, Node
from pathlib import Path
import json, math, struct


def run():
    robot=Robot()
    root=Path(__file__).resolve().parents[3]
    devices=[robot.getDeviceByIndex(i) for i in range(robot.getNumberOfDevices())]
    motors=[d for d in devices if d.getNodeType()==Node.ROTATIONAL_MOTOR]
    for motor in motors:
        motor.setPosition(float('inf'));motor.setVelocity(.7)
    sensors=[robot.getDevice('ps'+str(i)) for i in range(8)]
    gps=robot.getDevice('gps')
    for sensor in [*sensors,gps]:sensor.enable(16)
    emitter=robot.getDevice('emitter');receiver=robot.getDevice('receiver');receiver.enable(16)
    (root/'device-info.json').write_text(json.dumps([dict(name=d.getName(),type=type(d).__name__) for d in devices]))
    stats=dict(distance_m=0.,game_replies=0,turn_steps=0,sensor_samples=0,relocation_notices=0,elapsed_seconds=0.)
    previous=None;last_position_time=-1.;progress_origin=None;progress_time=0.;last_request=-1.;last_save=-1.;battery=100.;turn_until=0.;direction=1
    while robot.step(16)!=-1:
        now=robot.getTime();position=gps.getValues()
        assert all(math.isfinite(v) for v in position)
        if now-last_position_time>=1:
            if previous is not None:
                distance=math.hypot(position[0]-previous[0],position[2]-previous[2])
                if .006<distance<.06:stats['distance_m']+=distance
            previous=position;last_position_time=now
        readings=[s.getValue() for s in sensors]
        assert all(math.isfinite(v) for v in readings)
        stats['sensor_samples']+=1
        if progress_origin is None or now<turn_until:progress_origin=position;progress_time=now
        if now-progress_time>=4:
            if math.hypot(position[0]-progress_origin[0],position[2]-progress_origin[2])<.015:
                turn_until=now+4;direction=1
            progress_origin=position;progress_time=now
        if now>turn_until and min(readings[0],readings[7])<.035:
            direction=1 if readings[2]+readings[1]>readings[5]+readings[6] else -1
            turn_until=now+3.5
        if now<turn_until:
            speeds=(direction*.7,-direction*.7);stats['turn_steps']+=1
        else:speeds=(.7,.7)
        if battery<20:speeds=(0.,0.)
        for motor,speed in zip(motors,speeds):motor.setVelocity(speed)
        if now-last_request>=1:
            emitter.send(b'G');last_request=now
        while receiver.getQueueLength():
            packet=receiver.getBytes();receiver.nextPacket()
            if len(packet)==20:
                kind,score,sim,real,battery=struct.unpack('c f i i f',packet)
                info=dict(kind=kind.decode(),score=score,simulation_remaining=sim,real_remaining=real,battery=battery)
                assert kind==b'G' and 0<=battery<=100
                stats['game_replies']+=1
                (root/'game-info.json').write_text(json.dumps(info))
            elif packet==b'L':stats['relocation_notices']+=1;previous=None
        if now-last_save>=1:
            stats.update(elapsed_seconds=now,last_battery=battery,last_ranges=readings,position=position)
            (root/'autonomous-info.json').write_text(json.dumps(stats));last_save=now

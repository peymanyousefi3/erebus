"""2027 battery rules, adapted from sebybritez/Bater-a-PRUEBA.

Retains its speed-proportional calibration: 0.02 percentage points per
reference 16 ms at full speed. This is a game model, not electrical physics.
All rates come from the supervisor's configuration, never controller data.
"""
from pathlib import Path
import math
import json


class Battery:
    REFERENCE_STEP = 0.016

    def __init__(self, robot_num, rws, config_path=None):
        self._num = robot_num
        self._rws = rws
        self.level = 100.0
        self._last_sent = None
        self._last_send_time = -1.0
        self._contact = None
        self._stationary_since = None
        self._replaced = False
        self._last_time = None
        path = Path(config_path) if config_path else Path(__file__).with_name('sensorEnergyConfig.txt')
        self.settings = {}
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            line = line.split('#', 1)[0].strip().rstrip(',')
            if not line:
                continue
            key, text = line.split('=', 1)
            value = float(text)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'Invalid energy setting at {path}:{number}')
            self.settings[key.strip().lower().replace('_', '').replace(' ', '')] = value
        self.motor_max_velocity = self.settings['motormaxvelocity']
        self.motor_rate = self.settings['motordrainperstep'] / self.REFERENCE_STEP
        self.passive_rate = self.settings['batteryperstep'] / self.REFERENCE_STEP
        self.change_battery_time = self.settings['changebatterytime']
        self.swamp_multiplier = self.settings['swampmultiplier']
        if self.motor_max_velocity <= 0 or self.change_battery_time <= 0 or self.swamp_multiplier <= 1:
            raise ValueError('Energy configuration requires positive speed/replacement time and swamp multiplier > 1')

    def reset(self, time_elapsed=0.0, sensor_types=()):
        self.level = 100.0
        self._last_time = time_elapsed
        self._last_sent = None
        self._contact = None
        self._stationary_since = None
        self._replaced = False
        self.sensor_rate = sum(self.settings.get(name.lower(), 0.0) for name in sensor_types)
        self.publish(time_elapsed, force=True)

    @property
    def is_depleted(self):
        return self.level <= 0.0

    def publish(self, time_elapsed, force=False):
        value = round(self.level, 2)
        if force or (value != self._last_sent and time_elapsed - self._last_send_time >= 0.2):
            self._rws.send('batteryUpdate', f'{self._num},{value:.2f}')
            self._last_sent = value
            self._last_send_time = time_elapsed

    def update(self, time_elapsed, wheel_speeds, in_swamp=False):
        if self._last_time is None:
            self.reset(time_elapsed)
        dt = time_elapsed - self._last_time
        if not math.isfinite(dt) or dt < 0:
            raise ValueError('Battery clock must advance monotonically')
        if not wheel_speeds or any(not math.isfinite(v) for v in wheel_speeds):
            raise ValueError('Battery requires measured wheel speeds')
        # Pair-equivalent sum preserves the reference rate for two wheels;
        # additional powered wheels cannot reduce consumption by averaging.
        factor = sum(min(abs(v) / self.motor_max_velocity, 1.0) for v in wheel_speeds) / 2.0
        motor_drain = self.motor_rate * factor
        if in_swamp:
            motor_drain *= self.swamp_multiplier
        self.level = max(0.0, self.level - dt * (self.passive_rate + self.sensor_rate + motor_drain))
        self._last_time = time_elapsed
        self.publish(time_elapsed, force=self.is_depleted)

    def contact(self, tile, stationary, time_elapsed):
        """Require a continuous stop on this particular tile; never revive zero."""
        if tile is not self._contact:
            self._contact = tile
            self._stationary_since = None
            self._replaced = False
        if tile is None or not stationary:
            self._stationary_since = None
            self._replaced = False
            return False
        if self.is_depleted or self._replaced:
            return False
        if self._stationary_since is None:
            self._stationary_since = time_elapsed
        if time_elapsed - self._stationary_since >= self.change_battery_time:
            self.level = 100.0
            self._replaced = True
            self.publish(time_elapsed, force=True)
            return True
        return False


class WheelSpeedMonitor:
    """Observe wheel bodies through the named-node API shared by both engines."""
    def __init__(self, robot):
        self.robot = robot
        names = [f'EREBUS_WHEEL_{i}' for i in range(1, 5)]
        self.wheel_names = [name for name in names if robot.getFromProtoDef(name) is not None]
        if not self.wheel_names:
            self.wheel_names = [name for name in ('EPUCK_LEFT_WHEEL', 'EPUCK_RIGHT_WHEEL')
                                if robot.getFromProtoDef(name) is not None]
        if not self.wheel_names:
            raise ValueError('No measurable wheels: regenerate this robot from its JSON')

    @property
    def wheels(self):
        # PROTO parameter updates invalidate internal handles, including after
        # placing the robot. Reacquire up to four named nodes, not cached refs.
        wheels = [self.robot.getFromProtoDef(name) for name in self.wheel_names]
        if any(node is None for node in wheels):
            raise ValueError('A wheel body is unavailable')
        return wheels

    def speeds(self):
        chassis = self.robot.getVelocity()[3:6]
        return [math.sqrt(sum((v - c) ** 2 for v, c in zip(wheel.getVelocity()[3:6], chassis)))
                for wheel in self.wheels]


def sensor_types_from_proto(path):
    """Read the accepted device inventory from the organizer-owned model source."""
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("# energy_sensors: "):
            values = json.loads(line.partition(": ")[2])
            if isinstance(values, list) and all(isinstance(v, str) for v in values):
                return values
            raise ValueError("Invalid sensor inventory in robot model")
    raise ValueError("Robot has no energy inventory: regenerate it from its JSON")

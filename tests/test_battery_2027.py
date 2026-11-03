"""2027 energy and replacement regression, no simulator needed."""
import ast
import math
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from tempfile import TemporaryDirectory

main = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(main))
from battery import Battery, WheelSpeedMonitor, sensor_types_from_proto
messages = []
rws = NS(send=lambda *args: messages.append(args))

def drain(speed, step, duration=10, swamp=False, wheels=2):
    b = Battery(0, rws)
    b.reset()
    for i in range(round(duration / step)):
        b.update((i+1)*step, [speed]*wheels, swamp)
    return b

assert drain(0, .016).level == 100
assert math.isclose(drain(6.28, .016).level, 87.5)
assert math.isclose(drain(-6.28, .032).level, 87.52)  # 9.984 s
assert math.isclose(drain(3.14, .1).level, 93.75)
assert math.isclose(drain(6.28, .1).level, drain(6.28, .016).level)
assert math.isclose(drain(6.28, .1, swamp=True).level, 37.5)
assert math.isclose(drain(6.28, .1, wheels=4).level, 75)
assert math.isclose(drain(100, .1).level, 87.5)
b = drain(6.28, .1)
a, c = object(), object()
assert not b.contact(a, True, 10)
assert not b.contact(a, True, 14.999)
assert b.contact(a, True, 15) and b.level == 100
b.level = 50
assert not b.contact(a, True, 30)  # no repeated replacement during same stop
assert not b.contact(a, False, 30)
assert not b.contact(a, True, 31)
assert not b.contact(a, True, 35.999)
assert b.contact(a, True, 36)
b.level = 50
assert not b.contact(c, True, 37)  # new tile cannot inherit elapsed stop
assert not b.contact(None, True, 42)
assert not b.contact(c, True, 43)
assert b.contact(c, True, 48)
b.level = 0
assert not b.contact(a, True, 100)
assert not b.contact(a, True, 105) and b.is_depleted
b.reset(106)
assert b.level == 100 and not b.is_depleted
b.update(106, [0, 0])
try:
    b.update(105, [0, 0])
except ValueError:
    pass
else:
    raise AssertionError('Backwards clock accepted')
with TemporaryDirectory() as tmp:
    cfg = Path(tmp)/'energy.txt'
    original=(main/'sensorEnergyConfig.txt').read_text()
    cfg.write_text(original.replace('Camera = 0.0', 'Camera = 0.25'))
    b = Battery(0, rws, cfg)
    b.reset(sensor_types=['Camera', 'Camera'])
    b.update(2, [0, 0])
    assert b.level == 99
    cfg.write_text(original.replace('ChangeBatteryTime = 5', 'ChangeBatteryTime = nan'))
    try:
        Battery(0, rws, cfg)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid organizer configuration accepted')
# Real scanner code: arbitrary wheel placement, chassis rotation subtraction,
# and no reliance on controller-writable customData.
wheels=[NS(getVelocity=lambda: [0,0,0,6.28,2,0]), NS(getVelocity=lambda: [0,0,0,-6.28,2,0])]
for names in (['EPUCK_LEFT_WHEEL','EPUCK_RIGHT_WHEEL'],['EREBUS_WHEEL_1','EREBUS_WHEEL_2']):
    mapping=dict(zip(names,wheels))
    root=NS(getFromProtoDef=mapping.get,getVelocity=lambda: [0,0,0,0,2,0])
    monitor=WheelSpeedMonitor(root)
    assert monitor.speeds() == [6.28,6.28]
# The actual supervisor must terminate before packet processing, and always
# use the existing score/replay/removal path, including when time also expires.
source=(main/'MainSupervisor.py').read_text()
assert source.index('if self.robot_obj.battery.is_depleted:') < source.index('received_data = self._receiver.getBytes()')
assert 'frameTime *= self._time_muliplier' not in source
assert not any(isinstance(n, ast.Constant) and n.value == 'customData' for n in ast.walk(ast.parse((main/'battery.py').read_text())))
print('PASS: forward/reverse/half/zero/four-wheel drain, timestep invariance, swamp drain, continuous per-tile stops, movement reset, zero terminal state, sensor rates, config validation, trusted wheel scanner and ending order.')

with TemporaryDirectory() as tmp:
    path = Path(tmp)/"model.proto"
    path.write_text('# energy_sensors: ["Camera", "GPS"]\nPROTO custom_robot [ ] { Robot {} }')
    assert sensor_types_from_proto(path) == ["Camera", "GPS"]
    path.write_text("PROTO custom_robot [ ] { Robot {} }")
    try:
        sensor_types_from_proto(path)
    except ValueError:
        pass
    else:
        raise AssertionError("Missing organizer inventory accepted")

# Retained models must fail before importing a robot with pending field updates.
init_source=source[source.index("    def _game_init("):source.index("    def relocate_robot(")]
assert init_source.index("sensor_types_from_proto(") < init_source.index("self._add_robot()")
assert init_source.index("self.robot_obj.set_node(robot_node)") < init_source.index("field.setSFFloat(value)")

recovery=source[source.index("            except (ValueError, OSError) as error:"):source.index("        if self._run_tests:",source.index("            except (ValueError, OSError) as error:"))]
assert "simulationSetMode" not in recovery

"""Targeted first-iteration checks. Camera images are never saved."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from feasibility import Camera, advance

assert advance(0, 0, 0, -1, 0, 1)[0] == 0
assert advance(99, 0, 0, 1, 0, 1)[0] == 100
assert advance(50, 0, 0, 0, 1, 1)[1] > 0
assert advance(0, 0, 0, 0, 1, 1)[1] == 0
one = advance(45, 0, 0, 0, 1, 1)
half = advance(45, 0, 0, 0, 1, .5)
two = advance(*half, 0, 1, .5)
assert all(abs(a-b) < 1e-9 for a, b in zip(one, two))
print('PASS: speed bounds, stationary steering and constant-speed frame independence')
camera = Camera(0)
seen_frames = seen_faces = 0
last_stamp = 0
statuses = set()
deadline = time.monotonic() + 12
try:
    while time.monotonic() < deadline:
        frame, yaw, stamp, status = camera.read()
        if stamp != last_stamp:
            seen_frames += int(frame is not None)
            seen_faces += int(yaw is not None)
            last_stamp = stamp
            statuses.add(status)
        time.sleep(.05)
finally:
    camera.close()
result = {'camera_frames_observed': seen_frames, 'face_estimates_observed': seen_faces,
          'statuses': sorted(statuses), 'video_saved': False,
          'remaining_checks': ['user calibration', 'head-turn classification', 'audible speech', 'interactive WASD controls']}
print(json.dumps(result, indent=2))
(Path(__file__).parent / 'evidence/feasibility-check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')

from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'src'))
from monitoring import Monitor, valid_camera_sample

monitor=Monitor()
valid=valid_camera_sample(('frame',(0,0,0),10,'Face tracked'),10.1)
assert valid[1]==(0,0,0)
assert monitor.classify(valid[1],(0,0),10.1)[0]=='Facing forward'
stale=valid_camera_sample(('frame',(0,0,.9),10,'Face tracked'),10.8)
assert stale[0] is None and stale[1] is None
assert monitor.classify(stale[1],(0,0),10.8)==('Unavailable','Unknown',None)
invalid=valid_camera_sample(('frame',(float('nan'),0,0),11,'Face tracked'),11)
assert invalid[1] is None
missing=valid_camera_sample(('frame',None,12,'Face unavailable'),12)
assert monitor.classify(missing[1],(0,0),12)==('Unavailable','Unknown',None)
assert monitor.classify((0,0,0),(0,0),13)[0]=='Facing forward'
print('PASS: valid zero, stale, invalid, missing and recovered camera observations')

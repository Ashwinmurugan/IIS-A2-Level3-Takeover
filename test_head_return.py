from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'src'))
from driving import Driving

def step(car,seconds,head):
    for _ in range(round(seconds*100)):
        car.update(.01,0,0,head)

for direction in ('Looking left','Looking right'):
    events=[]
    car=Driving(lambda *e:events.append(e))
    car.distance=300
    car.automate()
    step(car,1.1,'Facing forward')
    step(car,2.1,direction)
    assert any(e[1]=='Please face the road ahead and take control.' for e in events)
    step(car,.5,'Facing forward')
    assert not any('Forward head cue stable' in e[0] for e in events)
    step(car,.1,'Unavailable')
    step(car,1.5,'Facing forward')
    assert sum('Forward head cue stable' in e[0] for e in events)==1
    assert any(e[1]=='Take control.' for e in events)
    step(car,.2,'Facing forward')
    assert sum('Forward head cue stable' in e[0] for e in events)==1
    assert car.mode=='Automated driving'
    car.manual()
    before=len(events)
    step(car,2,'Looking left')
    assert not any('Attention prompt' in e[0] for e in events[before:])
print('PASS: left/right prompts, stable forward reminder, unavailable reset, no repeated reminders or automatic takeover')

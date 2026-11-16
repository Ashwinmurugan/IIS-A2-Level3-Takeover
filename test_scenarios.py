"""Behavioural checks use synthetic sensor states, no webcam or speech."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'src'))
from driving import Driving
from scenarios import load_settings

settings = load_settings()
results = []

def car(name='tunnel', config=None):
    return Driving(lambda *event: None,name,config or copy.deepcopy(settings))

def run(vehicle, seconds, fps=60):
    for _ in range(int(seconds*fps)):
        vehicle.update(1/fps,0,0,'Unavailable')

for fps in (30,60,120):
    for speed in (20,45,100):
        v = car()
        v.speed = speed
        v.automate()
        run(v,150,fps)
        assert v.mode == 'Stopped' and v.distance < v.boundary
results.append('Tunnel stops before boundary at 3 speeds and 3 update rates')
events = []
v = Driving(lambda *event:events.append(event))
v.distance = 701
run(v,1)
assert sum('Tunnel passed' in e[1] for e in events) == 1
assert v.mode == 'Manual control'
results.append('Tunnel exit announced once without automatic engagement')
for initial in (.2,.4,.6,1.3):
    v=car(); v.position=initial; v.automate()
    before=v.position; run(v,.1)
    assert v.position != v.target and abs(v.position-v.target)<abs(before-v.target)
    run(v,10)
    assert abs(v.position-v.target)<.03
results.append('Current lane centring remains smooth from both lanes')
v=car('obstacle'); run(v,7)
assert not v.detected
run(v,2); assert v.detected
v=car('obstacle'); v.automate(); run(v,80)
assert v.mode=='Stopped' and not v.collision and v.distance < v.config['obstacle_at']
results.append('Obstacle appears dynamically and default no-response run stops safely in simulation')
v=car('obstacle'); v.position=0; v.automate(); run(v,40)
assert not v.stage and not v.collision
results.append('Adjacent lane obstacle does not request takeover')
c=copy.deepcopy(settings); c['obstacle'].update(start_speed=100,event_at=100,obstacle_at=165)
v=car('obstacle',c); v.distance=100; v.mode='Automated driving'; v.update(.01,0,0,'Facing forward')
assert v.mode=='Emergency braking'
v.manual(); assert v.pending_manual
run(v,20); assert v.mode=='Manual control' and not v.collision
results.append('Emergency braking starts immediately and queued takeover completes after stopping')
c['obstacle']['obstacle_at']=105
v=car('obstacle',c); v.distance=100; run(v,2)
assert v.collision
results.append('Impossible stopping distance produces an explicit collision outcome')
v=car('rain'); v.automate(); run(v,100)
assert v.mode=='Stopped' and v.rain_intensity==0 and not v.rain_restricted
results.append('Rain triggers reduction, takeover, fallback and stable visibility recovery while stopped')
v=car('rain'); v.distance=500; run(v,9); v.automate()
assert v.mode=='Manual control' and 'visibility' in v.notice
v.manual(); run(v,40); assert not v.rain_restricted
v.automate(); assert v.mode=='Automated driving'
results.append('Rain blocks automation and permits explicit re-engagement after recovery')
for result in results:
    print('PASS:',result)
(Path(__file__).parent/'evidence/phase5-checks.json').write_text(json.dumps(results,indent=2))

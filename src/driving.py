"""Deterministic desktop simulation. All thresholds are experimental."""
import math


class Driving:
    def __init__(self, emit):
        self.emit = emit
        self.speed = 45.0
        self.position = 1.0
        self.distance = 0.0
        self.boundary = 500.0
        self.mode = 'Manual control'
        self.target = 1.0
        self.steer = 0.0
        self.signal = 0
        self.lane = 1
        self.stage = 0
        self.away = 0.0
        self.prompted = False
        self.centred = True
        self.crossed = False
        self.lane_settle = 0.0
        self.message = 'F activates automated driving'

    def announce(self, message, spoken=''):
        self.emit(message, spoken)

    def manual(self):
        if self.mode != 'Manual control':
            self.mode = 'Manual control'
            self.stage = 0
            self.message = 'You are driving'
            self.announce('Space pressed: manual control; automatic braking cancelled', 'Manual control. You are driving.')

    def automate(self):
        if self.mode != 'Manual control':
            return
        remaining = self.boundary - self.distance
        if self.speed < 1 or remaining / max(self.speed / 3.6, .1) <= 15:
            self.announce('Automation unavailable: stopped or too near boundary')
            return
        self.lane = 1 if self.position >= .5 else 0
        self.target = float(self.lane)
        self.mode = 'Automated driving'
        self.centred = False
        self.stage, self.away, self.prompted = 0, 0.0, False
        self.message = 'Centring in current lane'
        self.announce('F pressed: automation active; gradual lane centring', 'Automated driving active.')

    def indicate(self, direction):
        self.signal = 0 if self.signal == direction else direction
        self.announce({-1: 'Left indicator on', 1: 'Right indicator on', 0: 'Indicator cancelled'}[self.signal])

    def update(self, dt, throttle, steer, head):
        old_speed = self.speed
        remaining = self.boundary - self.distance
        ttb = remaining / max(self.speed / 3.6, .1)
        if self.mode == 'Automated driving':
            if ttb <= 15 and self.stage == 0:
                self.stage = 1
                self.message = 'TAKE CONTROL - automation ends at tunnel'
                self.announce(f'Tunnel from scenario data: {remaining:.0f}m / {ttb:.1f}s; takeover requested', 'Take control. Automated driving ends at the tunnel.')
            if self.stage:
                self.away = self.away + dt if head in ('Turned away', 'Looking left', 'Looking right', 'Looking up', 'Looking down', 'Eyes appear closed') else 0.0
                if self.away >= 2 and not self.prompted:
                    self.prompted = True
                    self.announce('Attention prompt after sustained cue: ' + head, 'Please face the road and take control.')
            if ttb <= 10 and self.stage == 1:
                self.stage = 2
                self.message = 'TAKE CONTROL NOW'
                self.announce('Urgent warning: takeover still unconfirmed', 'Take control now.')
            stopping_distance = (self.speed / 3.6) ** 2 / (2 * 2.5)
            if self.stage and (ttb <= 6 or remaining <= stopping_distance + 15):
                self.mode = 'Automatic slowing'
                self.stage = 3
                self.message = 'Slowing automatically - SPACE to take control'
                self.announce('Response deadline: simulated deceleration at 2.5 m/s squared', 'Slowing automatically. Take control when ready.')
        if self.mode == 'Manual control':
            self.speed = max(0.0, min(100.0, self.speed + throttle * 18 * dt))
            desired = steer
        else:
            desired = max(-1.0, min(1.0, (self.target - self.position) * 2))
            if self.mode == 'Automatic slowing':
                self.speed = max(0.0, self.speed - 9 * dt)
                if self.speed == 0:
                    self.mode = 'Stopped'
                    self.message = 'Stopped - SPACE for manual control'
                    self.announce('Simulated vehicle stopped', 'Vehicle stopped.')
        previous_position = self.position
        self.steer += (desired - self.steer) * (1 - math.exp(-8 * dt))
        self.position = max(-.45, min(1.45, self.position + self.steer * self.speed / 100 * dt))
        if self.mode != 'Manual control' and (self.target-previous_position)*(self.target-self.position) <= 0:
            self.position = self.target
            self.steer = 0.0
        self.distance += (old_speed + self.speed) / 7.2 * dt
        new_lane = 1 if self.position >= .5 else 0
        if new_lane != self.lane:
            self.lane = new_lane
            self.lane_settle = 0
            self.announce(f'Lane marking crossed; lane {self.lane + 1}; indicator {self.signal}')
        if self.signal and abs(self.position - self.lane) < .08 and abs(self.steer) < .15:
            self.lane_settle += dt
            if self.lane_settle >= 1:
                self.signal = 0
                self.announce('Lane settled; indicator cancelled')
        else:
            self.lane_settle = 0
        if self.mode != 'Manual control' and not self.centred and abs(self.position-self.target) < .03:
            self.centred = True
            self.announce('Current lane centre reached')
            if not self.stage:
                self.message = 'Following lane'
        if self.distance >= self.boundary and not self.crossed:
            self.crossed = True
            self.announce('Tunnel boundary crossed in ' + self.mode)


def verify():
    records = []
    car = Driving(lambda *entry: records.append(entry))
    car.position = .35
    car.automate()
    assert car.position == .35
    car.update(.02, 0, 0, 'Unavailable')
    assert 0 < car.position < .35
    for _ in range(4000):
        car.update(.02, 0, 0, 'Unavailable')
    assert car.mode == 'Stopped' and car.distance < car.boundary
    before = car.distance, car.position, car.speed
    car.manual()
    assert before == (car.distance, car.position, car.speed)
    car = Driving(lambda *entry: records.append(entry))
    car.distance = 300
    car.automate()
    for _ in range(220):
        car.update(.02, 0, 0, 'Turned away')
    assert car.prompted
    car.manual()
    car.update(.02, 0, 0, 'Turned away')
    assert car.mode == 'Manual control' and car.stage == 0
    for initial in (.15, .35, .65, 1.3):
        sample = Driving(lambda *entry: None)
        sample.position = initial
        sample.automate()
        for _ in range(1000):
            sample.update(.01,0,0,'Facing forward')
        assert abs(sample.position - sample.target) < .03
    for fps in (30, 60, 120):
        for speed in (20, 45, 100):
            sample = Driving(lambda *entry: None)
            sample.speed = speed
            sample.automate()
            for _ in range(fps * 120):
                sample.update(1/fps, 0, 0, 'Facing forward')
            assert sample.mode == 'Stopped' and sample.distance < sample.boundary
    print('PASS: gradual centring, missing-camera fallback, stop before boundary, takeover continuity, attention prompt')


if __name__ == '__main__':
    verify()

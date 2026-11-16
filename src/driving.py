"""Configurable desktop simulation. Parameters are experimental, not certified."""
import math
import time
from scenarios import load_settings


class Driving:
    def __init__(self, emit, scenario='tunnel', settings=None):
        self.emit, self.scenario = emit, scenario
        self.settings = settings or load_settings()
        self.config, self.rules = self.settings[scenario], self.settings['rules']
        self.speed = self.config['start_speed']
        self.position = float(self.config['start_lane'])
        self.lane = self.config['start_lane']
        self.target = self.position
        self.distance = self.elapsed = self.steer = 0.0
        self.boundary = self.config['event_at']
        self.tunnel_length = self.config.get('tunnel_length',0)
        self.mode = 'Manual control'
        self.signal = self.stage = 0
        self.hazards = self.prompted = self.crossed = self.exited = False
        self.centred = True
        self.away = self.lane_settle = 0.0
        self.notice = ''
        self.notice_until = 0.0
        self.last_rejection = -100.0
        self.message = 'F activates automated driving'
        self.reason = ''
        self.request_at = None
        self.event_started = self.detected = self.collision = False
        self.rain_started = None
        self.rain_intensity = 0.0
        self.visibility = 220.0
        self.recovery_time = 0.0
        self.rain_restricted = False
        self.pending_manual = False

    def announce(self, message, spoken=''):
        self.emit(message, spoken)

    def notice_message(self, message, spoken=''):
        self.notice, self.notice_until = message, time.monotonic()+5
        self.announce(message, spoken)

    @property
    def gap(self):
        return self.config.get('obstacle_at',self.boundary)-self.distance

    @property
    def obstacle_threat(self):
        return self.detected and self.gap > 0 and abs(self.position-self.config['obstacle_lane']) < .45

    @property
    def location_label(self):
        if self.scenario == 'rain':
            return f'Visibility {self.visibility:.0f} m' if self.event_started else 'Clear weather'
        if self.scenario == 'obstacle':
            return f'Obstacle {max(0,self.gap):.0f} m' if self.detected and self.gap > 0 else 'Road ahead'
        if self.distance < self.boundary:
            return f'{self.boundary-self.distance:.0f} m to tunnel'
        return 'Inside tunnel' if self.distance < self.boundary+self.tunnel_length else 'Tunnel passed'

    def manual(self):
        if self.mode == 'Emergency braking':
            self.pending_manual = True
            self.notice_message('Emergency braking active. Manual control after stopping.', 'Emergency braking active.')
            return
        if self.mode != 'Manual control' and not self.collision:
            self.mode, self.stage, self.request_at = 'Manual control',0,None
            self.notice = ''
            if self.hazards:
                self.hazards, self.signal = False,0
                self.announce('Automatic hazard lights cleared by manual takeover')
            self.message = 'You are driving'
            self.announce('Space pressed: manual control; fallback braking cancelled','Manual control. You are driving.')

    def rejection_reason(self):
        if self.collision:
            return 'Collision recorded. Restart scenario.'
        if self.speed < 1:
            return 'Automation unavailable while stopped.'
        if self.scenario == 'tunnel':
            if self.boundary <= self.distance < self.boundary+self.tunnel_length:
                return 'Automation unavailable inside tunnel.'
            if 0 < self.boundary-self.distance <= self.speed/3.6*self.rules['request_seconds']:
                return 'Automation unavailable - tunnel ahead.'
        if self.scenario == 'rain' and self.rain_restricted:
            return 'Automation unavailable - visibility below limit.'
        if self.scenario == 'obstacle' and self.obstacle_threat:
            return 'Automation unavailable - stopped vehicle ahead.'
        return ''

    def automate(self):
        if self.mode != 'Manual control':
            return
        reason = self.rejection_reason()
        if reason:
            now = time.monotonic()
            spoken = reason if now-self.last_rejection >= 4 else ''
            if spoken:
                self.last_rejection = now
            self.notice_message(reason,spoken)
            return
        self.notice = ''
        self.lane = 1 if self.position >= .5 else 0
        self.target, self.mode = float(self.lane),'Automated driving'
        self.centred = False
        self.stage, self.away, self.prompted = 0,0.0,False
        self.request_at = None
        self.message = 'Centring in current lane'
        self.announce('F pressed: automation active; gradual lane centring','Automated driving active.')

    def indicate(self, direction):
        if self.hazards:
            self.announce('Direction signal ignored while automatic hazards are active')
            return
        self.signal = 0 if self.signal == direction else direction
        self.announce({-1:'Left indicator on',1:'Right indicator on',0:'Indicator cancelled'}[self.signal])

    def observe(self, dt):
        if self.scenario == 'tunnel':
            if self.distance >= self.boundary and not self.crossed:
                self.crossed = True
                self.announce('Tunnel entered in '+self.mode)
            if self.distance >= self.boundary+self.tunnel_length and not self.exited:
                self.exited = True
                message = 'Tunnel passed. Automated driving is available.' if self.speed >= 1 else 'Tunnel passed. Accelerate manually before activating automation.'
                self.notice_message(message,message)
        elif self.scenario == 'obstacle':
            if self.distance >= self.config['event_at'] and not self.event_started:
                self.event_started = True
                self.announce('Scenario event: stationary vehicle appeared; sensing pending')
            if self.event_started and 0 < self.gap <= self.config['detection_range'] and not self.detected:
                self.detected = True
                self.announce(f'Simulated sensor: stationary vehicle, lane {self.config["obstacle_lane"]+1}, gap {self.gap:.0f} m, closing speed {self.speed:.0f} km/h')
        else:
            if self.distance >= self.boundary and self.rain_started is None:
                self.rain_started = self.elapsed
                self.event_started = True
                self.announce('Rain started; simulated visibility declining')
            if self.rain_started is not None:
                age = self.elapsed-self.rain_started
                self.rain_intensity = self.config['rain_peak']*max(0,min(1,age/8,(self.config['rain_duration']-age)/8))
                self.visibility = 220-210*self.rain_intensity
                if self.visibility < self.config['visibility_limit']:
                    if not self.rain_restricted:
                        self.announce(f'Visibility {self.visibility:.0f} m below configured operating limit')
                    self.rain_restricted, self.recovery_time = True,0
                elif self.rain_restricted:
                    self.recovery_time += dt
                    if self.recovery_time >= self.config['recovery_seconds']:
                        self.rain_restricted = False
                        message = 'Visibility recovered.' if self.speed < 1 else 'Visibility recovered. Automated driving is available.'
                        self.notice_message(message,message)

    def request(self, reason):
        if self.stage == 0:
            self.stage, self.reason, self.request_at = 1,reason,self.elapsed
            self.message = 'Obstruction ahead. Slow down and take control.' if self.scenario == 'obstacle' else 'Take control. '+reason
            self.announce('Takeover requested: '+reason,self.message)

    def brake(self, emergency=False):
        mode = 'Emergency braking' if emergency else 'Automatic slowing'
        if self.mode != mode:
            if self.mode == 'Manual control':
                self.target = float(1 if self.position >= .5 else 0)
            if emergency:
                stopping = (self.speed/3.6)**2/(2*self.rules['emergency_deceleration'])
                self.announce(f'Emergency decision: gap {self.gap:.1f} m; estimated braking distance {stopping:.1f} m; margin {self.rules["stop_margin"]} m')
            self.mode, self.hazards, self.signal = mode,True,0
            self.stage = 4 if emergency else 3
            self.message = 'Emergency braking - stopped vehicle ahead' if emergency else 'Slowing automatically'
            self.announce(self.message+'; hazard lights active',self.message)

    def update(self, dt, throttle, steer, head):
        if self.collision:
            return
        self.elapsed += dt
        self.observe(dt)
        old_speed = self.speed
        remaining = self.boundary-self.distance
        ttb = remaining/max(self.speed/3.6,.1)
        r = self.rules
        if self.mode == 'Automated driving':
            if self.scenario == 'tunnel' and 0 < ttb <= r['request_seconds']:
                self.request('Automation ends at tunnel.')
            if self.scenario == 'rain' and self.rain_restricted:
                self.request('Visibility is below the operating limit.')
            if self.scenario == 'obstacle' and self.obstacle_threat:
                self.request('Obstruction ahead. Slow down.')
        emergency_stop = (self.speed/3.6)**2/(2*r['emergency_deceleration'])
        if self.scenario == 'obstacle' and self.obstacle_threat and self.speed > 0 and self.gap <= emergency_stop+r['stop_margin']:
            self.brake(True)
        if self.stage in (1,2) and self.mode == 'Automated driving':
            self.away = self.away+dt if head in ('Turned away','Looking left','Looking right','Looking up','Looking down','Eyes appear closed') else 0
            if self.away >= r['attention_seconds'] and not self.prompted:
                self.prompted = True
                self.announce('Attention prompt after sustained cue: '+head,'Please face the road and take control.')
            age = self.elapsed-self.request_at
            urgent = ttb <= r['urgent_seconds'] if self.scenario == 'tunnel' else age >= r['request_seconds']-r['urgent_seconds']
            if urgent and self.stage == 1:
                self.stage = 2
                self.announce('Urgent warning: takeover still unconfirmed','Take control now.')
            stopping = (self.speed/3.6)**2/(2*r['deceleration'])
            fallback = age >= r['request_seconds']-r['fallback_seconds']
            if self.scenario == 'tunnel':
                fallback = ttb <= r['fallback_seconds'] or remaining <= stopping+r['stop_margin']
            if self.scenario == 'obstacle' and self.obstacle_threat:
                fallback = fallback or self.gap <= stopping+r['stop_margin']
            if fallback:
                self.brake()
        if self.mode == 'Manual control':
            self.speed = max(0,min(100,self.speed+throttle*18*dt))
            desired = steer
        else:
            desired = max(-1,min(1,(self.target-self.position)*2))
            deceleration = 0
            if self.mode in ('Automatic slowing','Emergency braking'):
                deceleration = r['emergency_deceleration'] if self.mode == 'Emergency braking' else r['deceleration']
            elif self.mode == 'Automated driving' and self.scenario == 'rain' and self.rain_intensity > .2 and self.speed > r['rain_speed']:
                self.speed = max(r['rain_speed'],self.speed-r['deceleration']*3.6*dt)
            if deceleration:
                self.speed = max(0,self.speed-deceleration*3.6*dt)
                if self.speed == 0:
                    self.mode = 'Stopped'
                    self.announce('Simulated vehicle stopped','Vehicle stopped.')
                    if self.pending_manual:
                        self.pending_manual = False
                        self.manual()
        previous_position = self.position
        self.steer += (desired-self.steer)*(1-math.exp(-8*dt))
        self.position = max(-.45,min(1.45,self.position+self.steer*self.speed/100*dt))
        if self.mode != 'Manual control' and (self.target-previous_position)*(self.target-self.position) <= 0:
            self.position,self.steer = self.target,0
        previous_distance = self.distance
        self.distance += (old_speed+self.speed)/7.2*dt
        if self.scenario == 'obstacle' and self.distance >= self.config['event_at'] and previous_distance < self.config['obstacle_at'] <= self.distance and abs(self.position-self.config['obstacle_lane']) < .45:
            self.collision,self.speed,self.mode,self.stage = True,0,'Collision recorded',4
            self.announce('Collision recorded: stopping margin insufficient. Restart scenario.','Collision recorded. Restart scenario.')
        new_lane = 1 if self.position >= .5 else 0
        if new_lane != self.lane:
            self.lane,self.lane_settle = new_lane,0
            self.announce(f'Lane marking crossed; lane {self.lane+1}; indicator {self.signal}')
        if self.signal and abs(self.position-self.lane) < .08 and abs(self.steer) < .15:
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

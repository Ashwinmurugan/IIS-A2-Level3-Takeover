"""Iteration 1: local webcam, keyboard driving and speech feasibility."""
import argparse
import json
from driving import Driving
from scenarios import load_settings, DEFAULT_PATH
from scene import draw_road, draw_log
from monitoring import Monitor, pose_from_rotation
from collections import deque
import math
import os
from pathlib import Path
import queue
import threading
import time

import cv2
import mediapipe as mp
import numpy as np
import pygame

ROOT = Path(__file__).resolve().parents[1]
BG, PANEL, WHITE, MUTED, TEAL, AMBER = '#101820', '#1b2834', '#eef4fa', '#9caebf', '#51dbc4', '#ffc369'


class Camera:
    def __init__(self, index):
        self.index = index
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.sample = (None, None, 0.0, 'Starting camera')
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def publish(self, frame, yaw, status):
        with self.lock:
            self.sample = (frame, yaw, time.monotonic(), status)

    def read(self):
        with self.lock:
            return self.sample

    def run(self):
        capture = None
        try:
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(ROOT / 'models/face_landmarker.task')),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_faces=1, output_facial_transformation_matrixes=True, output_face_blendshapes=True)
            with mp.tasks.vision.FaceLandmarker.create_from_options(options) as model:
                capture = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
                capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                if not capture.isOpened():
                    raise RuntimeError('Camera unavailable; check permissions or camera index')
                timestamp = 0
                while not self.stop.is_set():
                    ok, frame = capture.read()
                    if not ok:
                        self.publish(None, None, 'Camera frame unavailable')
                        self.stop.wait(0.1)
                        continue
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    timestamp = max(timestamp + 1, int(time.monotonic() * 1000))
                    result = model.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
                    yaw = None
                    if len(result.facial_transformation_matrixes):
                        rotation = result.facial_transformation_matrixes[0][:3, :3]
                        angles = pose_from_rotation(rotation)
                        scores = {item.category_name: item.score for item in result.face_blendshapes[0]} if result.face_blendshapes else {}
                        blink = min(scores.get('eyeBlinkLeft', float('nan')), scores.get('eyeBlinkRight', float('nan')))
                        yaw = (*angles, blink)
                    self.publish(rgb, yaw, 'Face tracked' if yaw is not None else 'Face unavailable')
        except Exception as error:
            self.publish(None, None, str(error))
        finally:
            if capture is not None:
                capture.release()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=3)


class Speech:
    def __init__(self, events):
        self.requests = queue.Queue()
        self.busy = threading.Event()
        self.events = events
        self.closed = threading.Event()
        threading.Thread(target=self.run, daemon=True).start()

    def say(self, message='Take control. Automated driving ends at the tunnel.'):
        self.requests.put(message)

    def run(self):
        import pythoncom
        pythoncom.CoInitialize()
        try:
            import win32com.client
            voice = win32com.client.Dispatch('SAPI.SpVoice')
            while not self.closed.wait(.02):
                message = None
                while not self.requests.empty():
                    message = self.requests.get_nowait()
                if message is not None:
                    voice.Speak(message, 3)  # Async, replace obsolete speech.
                    self.busy.set()
                    self.events.put('Speech: ' + message)
                if self.busy.is_set() and voice.Status.RunningState == 1:
                    self.busy.clear()
                    self.events.put('Speech completed')
            voice.Speak('', 3)
        except Exception as error:
            self.events.put('Speech unavailable: ' + str(error))
            self.busy.clear()
        finally:
            pythoncom.CoUninitialize()


def advance(speed, position, distance, throttle, steer, dt):
    speed = float(np.clip(speed + throttle * 18 * dt, 0, 100))
    position = float(np.clip(position + steer * speed / 100 * dt, -1.3, 1.3))
    return speed, position, distance + speed / 3.6 * dt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--no-camera', action='store_true')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--scenario', choices=['tunnel','obstacle','rain'], default='tunnel')
    parser.add_argument('--config', type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    try:
        settings = load_settings(args.config)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error('Invalid scenario configuration: '+str(error))
    selected_scenario = args.scenario
    scenario_names = ['tunnel','obstacle','rain']
    scenario_labels = ['1 Tunnel','2 Stopped vehicle','3 Heavy rain']
    scenario_buttons = [pygame.Rect(370+i*220,300,210,48) for i in range(3)]
    if args.smoke:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    pygame.init()
    screen = pygame.display.set_mode((1440, 850), pygame.RESIZABLE)
    pygame.display.set_caption('IIS A2 - Integrated tunnel simulation')
    canvas = pygame.Surface((1440, 850))
    font = pygame.font.SysFont('Segoe UI', 23)
    small = pygame.font.SysFont('Segoe UI', 20)
    heading = pygame.font.SysFont('Segoe UI', 28, bold=True)
    alert_font = pygame.font.SysFont('Segoe UI', 32, bold=True)
    events = queue.Queue()
    speech = None if args.smoke else Speech(events)
    camera = None if args.smoke or args.no_camera else Camera(args.camera)
    history = deque(maxlen=500)
    log_scroll = 0
    log_font = pygame.font.SysFont('Segoe UI', 22, bold=True)
    samples = deque()
    monitor = Monitor()
    started = False
    calibration_note = 'Press C to set your forward position'
    flashes = {}
    start_button = pygame.Rect(520, 488, 360, 54)
    baseline = None
    calibrating = False
    calibrated_at = 0.0
    speed, position, distance = 45.0, 0.0, 0.0
    manual = True
    clock = pygame.time.Clock()
    start = time.monotonic()
    previous_state = ''
    previous_eyes = ''
    state_since = start
    last_sample = 0.0
    running, frames = True, 0

    def log(message):
        history.append((time.monotonic() - start, message))

    def text(message, x, y, color=WHITE, face=None):
        canvas.blit((face or font).render(message, True, color), (x, y))

    def wrap(message, x, y, width=310, color=MUTED):
        line = ''
        for word in message.split():
            candidate = (line + ' ' + word).strip()
            if small.size(candidate)[0] > width and line:
                text(line, x, y, color, small)
                y += 25
                line = word
            else:
                line = candidate
        text(line, x, y, color, small)
        return y + 29

    records = []
    def emit(message, spoken=''):
        log(message)
        records.append({'seconds': round(time.monotonic()-start, 3), 'event': message})
        if spoken and speech:
            speech.say(spoken)
    car = Driving(emit, selected_scenario, settings)
    music = None
    music_enabled = False
    if pygame.mixer.get_init():
        rate = pygame.mixer.get_init()[0]
        t = np.arange(rate * 2) / rate
        wave = (np.sin(2*np.pi*220*t) + .3*np.sin(2*np.pi*330*t)) * 800
        music = pygame.sndarray.make_sound(np.column_stack((wave, wave)).astype(np.int16))
        channel = pygame.mixer.Channel(0)
    audio_paused = False
    emit('Scenario selected: '+selected_scenario+'; experimental thresholds')
    emit('Configuration: '+json.dumps(settings[selected_scenario]))
    try:
        while running:
            dt = min(clock.tick(60) / 1000, 0.1)
            now = time.monotonic()
            frame, yaw, stamp, status = camera.read() if camera else (None, None, 0, 'Camera disabled')
            fresh = now - stamp < 0.75
            if not fresh:
                yaw, frame = None, None
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not started:
                    mx, my = event.pos
                    mapped = (mx*1440/screen.get_width(), my*850/screen.get_height())
                    for index, button in enumerate(scenario_buttons):
                        if button.collidepoint(mapped):
                            selected_scenario = scenario_names[index]
                            car = Driving(emit, selected_scenario, settings)
                            emit('Scenario selected: '+selected_scenario)
                            emit('Configuration: '+json.dumps(settings[selected_scenario]))
                    if start_button.collidepoint(mapped):
                        started = True
                        emit('Drive started in right-hand lane')
                if event.type == pygame.MOUSEWHEEL:
                    log_scroll = max(0, log_scroll+event.y*3)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_PAGEUP:
                        log_scroll += 12
                    elif event.key == pygame.K_PAGEDOWN:
                        log_scroll = max(0,log_scroll-12)
                    elif event.key == pygame.K_END:
                        log_scroll = 0
                    flashes[event.key] = now + .3
                    if not started and event.key in (pygame.K_1,pygame.K_2,pygame.K_3):
                        selected_scenario = scenario_names[event.key-pygame.K_1]
                        car = Driving(emit, selected_scenario, settings)
                        emit('Scenario selected: '+selected_scenario)
                        emit('Configuration: '+json.dumps(settings[selected_scenario]))
                    if event.key == pygame.K_RETURN and not started:
                        started = True
                        emit('Drive started in right-hand lane')
                    if not started and event.key not in (pygame.K_c, pygame.K_ESCAPE, pygame.K_RETURN):
                        continue
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_c:
                        samples.clear()
                        calibrating, calibrated_at = True, now
                        baseline = None
                        calibration_note = 'Hold still with eyes open for two seconds'
                        emit('Calibration requested; face forward with eyes open')
                    elif event.key == pygame.K_t and speech:
                        speech.say('Take control. '+{'tunnel':'Automation ends at tunnel.','obstacle':'Stopped vehicle ahead.','rain':'Visibility is below the operating limit.'}[selected_scenario])
                    elif event.key == pygame.K_SPACE:
                        car.manual()
                    elif event.key == pygame.K_f:
                        car.automate()
                    elif event.key == pygame.K_TAB:
                        started = False
                        car = Driving(emit, selected_scenario, settings)
                        if speech:
                            speech.say('Choose a scenario.')
                        emit('Returned to scenario selection; run reset')
                    elif event.key == pygame.K_r:
                        car = Driving(emit, selected_scenario, settings)
                        if speech:
                            speech.say('Scenario reset. Manual control.')
                        emit('Scenario reset')
                    elif event.key == pygame.K_q:
                        car.indicate(-1)
                    elif event.key == pygame.K_e:
                        car.indicate(1)
                    elif event.key == pygame.K_m and music:
                        music_enabled = not music_enabled
                        if music_enabled:
                            channel.play(music, loops=-1)
                        else:
                            channel.stop()
                        emit('Demo audio ' + ('enabled' if music_enabled else 'disabled'))
            if calibrating:
                if yaw is not None and stamp != last_sample:
                    samples.append(yaw[:2])
                    last_sample = stamp
                if now - calibrated_at >= 2:
                    calibrating = False
                    if len(samples) >= 12 and max(np.std(samples, axis=0)) < 5:
                        baseline = tuple(np.median(samples, axis=0))
                        calibration_note = 'Forward position set'
                        emit(calibration_note)
                    else:
                        calibration_note = 'Calibration failed. Hold still and retry C.'
                        emit(calibration_note)
            state, eyes, relative = monitor.classify(yaw, baseline, now)
            if eyes != previous_eyes:
                if eyes == 'Eyes appear closed' or previous_eyes == 'Eyes appear closed':
                    emit('Eye cue: ' + eyes)
                previous_eyes = eyes
            if state != previous_state:
                previous_state, state_since = state, now
                emit('Head cue: ' + state)
            while not events.empty():
                emit(events.get_nowait())
            keys = pygame.key.get_pressed()
            manual = car.mode == 'Manual control'
            throttle = int(keys[pygame.K_w]) - int(keys[pygame.K_s])
            steering_input = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
            if started:
                car.update(dt, throttle, steering_input, 'Eyes appear closed' if eyes == 'Eyes appear closed' else state)
            speed, position, distance, steer = car.speed, car.position, car.distance, car.steer
            pause_audio = bool(car.stage or (speech and speech.busy.is_set()))
            if music_enabled and music:
                if pause_audio:
                    channel.pause()
                else:
                    channel.unpause()
            if pause_audio != audio_paused:
                audio_paused = pause_audio
                emit('Demo audio priority: ' + ('paused' if pause_audio else 'released'))

            canvas.fill(BG)
            text('LEVEL 3 / TAKEOVER INTERFACE', 24, 18, face=heading)
            text('Phase 5  /  Context-aware scenarios  |  TAB selects scenario', 24, 55, MUTED)
            for rect in [(16, 100, 306, 670), (336, 100, 724, 670), (1074, 100, 350, 670)]:
                pygame.draw.rect(canvas, PANEL, rect, border_radius=12)
            text('DRIVER MONITORING', 32, 118, TEAL)
            if frame is not None:
                preview = pygame.image.frombuffer(frame.tobytes(), (frame.shape[1], frame.shape[0]), 'RGB')
                preview = pygame.transform.flip(pygame.transform.scale(preview, (274, 206)), True, False)
                canvas.blit(preview, (32, 160))
            else:
                pygame.draw.rect(canvas, '#263747', (32, 160, 274, 206))
                wrap(status, 45, 230, 240)
            text(state, 32, 390, AMBER if state != 'Facing forward' else TEAL)
            text('Yaw / pitch: ' + ('--' if relative is None else f'{relative[0]:+.0f} / {relative[1]:+.0f}'), 32, 428)
            text(eyes, 32, 463, AMBER if eyes == 'Eyes appear closed' else MUTED)
            text(f'Head cue: {now - state_since:.1f}s', 32, 500, MUTED)
            wrap(calibration_note, 32, 540, 265, TEAL)
            wrap('C sets your forward reference for head turns. Eye closure is an estimate, not a sleep diagnosis. Camera frames stay local.', 32, 620, 265)
            text({'tunnel':'TUNNEL','obstacle':'STOPPED VEHICLE','rain':'HEAVY RAIN'}[selected_scenario], 354, 118, TEAL)
            text(car.location_label,780,118,MUTED)
            draw_road(canvas, car)
            notice_active = now < car.notice_until and bool(car.notice)
            denied = notice_active and 'unavailable' in car.notice.lower()
            active_alert = car.stage > 0 or denied
            alert_color = '#ef5959' if car.stage >= 2 else AMBER
            pygame.draw.rect(canvas, '#38212a' if active_alert else '#18212b', (354, 160, 688, 78))
            pygame.draw.rect(canvas, alert_color if active_alert else '#3b5266', (354, 160, 688, 78), 3)
            if active_alert:
                pygame.draw.polygon(canvas, alert_color, [(385,168),(359,224),(411,224)])
                text('!',377,181,BG,alert_font)
            title = {1:'TAKE CONTROL', 2:'TAKE CONTROL NOW', 3:'SLOWING AUTOMATICALLY',4:'EMERGENCY BRAKING'}.get(car.stage, car.mode)
            if car.collision:
                title = 'COLLISION RECORDED'
            if car.mode == 'Stopped':
                title = 'VEHICLE STOPPED'
            if denied:
                title = 'AUTOMATION UNAVAILABLE'
            text(title, 424, 164, alert_color if active_alert else WHITE, alert_font)
            detail = car.reason+' Press SPACE.' if car.stage in (1,2) else 'Braking active - preparing to stop' if car.stage == 4 else 'SPACE to take manual control' if car.stage else car.message
            if notice_active and not car.stage:
                detail = car.notice
            if car.collision:
                detail = 'Stopping margin insufficient. R restarts scenario.'
            detail_font = small if small.size(detail)[0] <= 605 else pygame.font.SysFont('Segoe UI',17)
            text(detail, 424, 207, WHITE, detail_font)
            text(f'{speed:05.1f} km/h', 380, 520, face=heading)
            text(car.mode, 680, 526, TEAL)
            text(f'Travelled {distance:.0f} m', 380, 568, MUTED)
            text(f'Lane {car.lane+1}  |  offset {position-car.lane:+.2f}', 680, 568, MUTED)
            wheel = (690, 650)
            pygame.draw.circle(canvas, '#91a3b2', wheel, 45, 5)
            angle = steer * .65
            dx, dy = math.cos(angle) * 39, math.sin(angle) * 39
            pygame.draw.line(canvas, WHITE, (690-dx, 650-dy), (690+dx, 650+dy), 5)
            for direction, cx in [(-1, 550), (1, 830)]:
                lit = (car.hazards or car.signal == direction) and int(now*2)%2 == 0
                arrow = [(-30,0),(-7,-22),(-7,-10),(27,-10),(27,10),(-7,10),(-7,22)]
                pygame.draw.polygon(canvas, AMBER if lit else '#344556', [(cx-x*direction,650+y) for x,y in arrow])
            if car.hazards:
                text('HAZARD LIGHTS ACTIVE', 550, 602, AMBER, small)
            text('Simulated seat / wheel vibration: ' + ('ON' if car.stage >= 2 else 'OFF'), 370, 704, AMBER)
            text('M demo audio: ' + ('paused for alert' if music_enabled and audio_paused else 'playing' if music_enabled else 'off'), 370, 735, MUTED)
            text('LIVE EVENT LOG', 1092, 118, TEAL)
            log_scroll = draw_log(canvas, history, log_font, log_scroll)
            controls = [('W','Speed +'),('S','Brake'),('A','Left'),('D','Right'),('Q','Signal'),('E','Signal'),('F','Auto'),('SPACE','Manual'),('R','Reset'),('C','Calibrate'),('M','Audio'),('T','Speech'),('ESC','Exit')]
            keycodes = [pygame.K_w,pygame.K_s,pygame.K_a,pygame.K_d,pygame.K_q,pygame.K_e,pygame.K_f,pygame.K_SPACE,pygame.K_r,pygame.K_c,pygame.K_m,pygame.K_t,pygame.K_ESCAPE]
            for i, ((label, action), code) in enumerate(zip(controls, keycodes)):
                x = 18+i*109
                pressed = keys[code] or flashes.get(code,0)>now
                pygame.draw.rect(canvas, TEAL if pressed else '#263747', (x,780,102,36), border_radius=6)
                text(label,x+10,784,BG if pressed else WHITE,small)
                text(action,x+5,818,MUTED,small)
            if not started:
                pygame.draw.rect(canvas, '#101e2b', (354,245,688,320), border_radius=12)
                text('Choose your scenario',400,258,WHITE,heading)
                for index, button in enumerate(scenario_buttons):
                    chosen = selected_scenario == scenario_names[index]
                    pygame.draw.rect(canvas,TEAL if chosen else '#314758',button,border_radius=8)
                    text(scenario_labels[index],button.x+10,button.y+12,BG if chosen else WHITE,small)
                text('C calibrates your forward position. Hold still.',380,365)
                text(f'Start {car.speed:.0f} km/h  |  lane {car.lane+1}  |  event at {car.boundary:.0f} m',380,405,MUTED,small)
                text('Parameters are editable in scenarios.json. TAB returns here.',380,445,MUTED,small)
                pygame.draw.rect(canvas,TEAL,start_button,border_radius=10)
                text('Start drive / ENTER',558,497,BG,heading)
            screen.blit(pygame.transform.smoothscale(canvas, screen.get_size()), (0, 0))
            pygame.display.flip()
            frames += 1
            if args.smoke:
                pygame.image.save(canvas,str(ROOT / f'evidence/phase5-{selected_scenario}-{frames}.png'))
                started = True
                if frames == 1:
                    car.distance = car.boundary
                    if selected_scenario == 'rain':
                        car.rain_started = car.elapsed-9
                        car.event_started = True
                if frames == 2:
                    car.mode = 'Automated driving'
                    car.request('Visibility is below the operating limit.' if selected_scenario == 'rain' else 'Stopped vehicle ahead.' if selected_scenario == 'obstacle' else 'Automation ends at tunnel.')
                if frames == 3:
                    print('PASS: scenario selection, scene and contextual alert rendered')
                    running = False
    except KeyboardInterrupt:
        emit('Session interrupted from terminal; clean shutdown')
    finally:
        if camera:
            camera.close()
        if speech:
            speech.closed.set()
        if not args.smoke:
            folder = ROOT / 'evidence/runs'
            folder.mkdir(exist_ok=True)
            (folder / (str(time.time_ns()) + '.json')).write_text(json.dumps(records, indent=2))
        pygame.quit()


if __name__ == '__main__':
    main()

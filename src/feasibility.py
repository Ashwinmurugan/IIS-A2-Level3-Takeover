"""Iteration 1: local webcam, keyboard driving and speech feasibility."""
import argparse
import json
from driving import Driving
from audio_priority import AudioPriority
from scenarios import load_settings, DEFAULT_PATH
from dashboard import CANVAS_SIZE, canvas_point, draw_dashboard, fit_view
from monitoring import Monitor, pose_from_rotation, valid_camera_sample
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
    def __init__(self, events, spotify_enabled=False):
        self.requests = queue.Queue()
        self.busy = threading.Event()
        self.events = events
        self.closed = threading.Event()
        self.spotify_enabled = threading.Event()
        if spotify_enabled:
            self.spotify_enabled.set()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def say(self, message='Take control. Automated driving ends at the tunnel.'):
        self.requests.put(message)

    def run(self):
        import pythoncom
        pythoncom.CoInitialize()
        priority = None
        try:
            import win32com.client
            voice = win32com.client.Dispatch('SAPI.SpVoice')
            try:
                priority = AudioPriority(self.events.put)
            except Exception as error:
                self.events.put('Other audio integration unavailable: '+str(error))
            while not self.closed.wait(.02):
                message = None
                while not self.requests.empty():
                    message = self.requests.get_nowait()
                if priority and not self.spotify_enabled.is_set():
                    priority.restore()
                if message is not None:
                    if priority and self.spotify_enabled.is_set():
                        priority.lower()
                    self.events.put('Warning speech prioritised')
                    voice.Speak(message, 3)  # Async, replace obsolete speech.
                    self.busy.set()
                    self.events.put('Speech: ' + message)
                if self.busy.is_set() and voice.Status.RunningState == 1:
                    self.busy.clear()
                    self.events.put('Speech completed')
                    if priority:
                        priority.restore()
            voice.Speak('', 3)
        except Exception as error:
            self.events.put('Speech unavailable: ' + str(error))
            self.busy.clear()
        finally:
            if priority:
                priority.restore()
            pythoncom.CoUninitialize()


def advance(speed, position, distance, throttle, steer, dt):
    speed = float(np.clip(speed + throttle * 18 * dt, 0, 100))
    position = float(np.clip(position + steer * speed / 100 * dt, -1.3, 1.3))
    return speed, position, distance + speed / 3.6 * dt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--no-camera', action='store_true')
    parser.add_argument('--audio-priority', '--spotify-priority', dest='spotify_priority', action='store_true', help='Lower Other audio audio during speech; restore afterwards')
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--windowed', action='store_true')
    parser.add_argument('--demo-view', action='store_true', help='Start with the simplified presentation view')
    parser.add_argument('--scenario', choices=['tunnel','obstacle','rain'], default='tunnel')
    parser.add_argument('--config', type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    try:
        settings = load_settings(args.config)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error('Invalid scenario configuration: '+str(error))
    selected_scenario = args.scenario
    scenario_names = ['tunnel','obstacle','rain']
    scenario_buttons = [pygame.Rect(370+i*220,300,210,48) for i in range(3)]
    if args.smoke:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    pygame.init()
    fullscreen = not (args.windowed or args.smoke)
    demo_view = args.demo_view
    screen = pygame.display.set_mode((0,0),pygame.FULLSCREEN) if fullscreen else pygame.display.set_mode((1440,850),pygame.RESIZABLE)
    pygame.display.set_caption('Level 3 Takeover Simulator')
    canvas = pygame.Surface(CANVAS_SIZE)
    events = queue.Queue()
    speech = None if args.smoke else Speech(events,args.spotify_priority)
    camera = None if args.smoke or args.no_camera else Camera(args.camera)
    history = deque(maxlen=500)
    log_scroll = 0
    samples = deque()
    monitor = Monitor()
    started = False
    calibration_dialog = True
    calibrate_button = pygame.Rect(460,458,245,58)
    skip_button = pygame.Rect(735,458,245,58)
    calibration_note = 'Press C to set your forward position'
    flashes = {}
    start_button = pygame.Rect(520, 488, 360, 54)
    change_button = pygame.Rect(1120, 24, 290, 48)
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
            frame, yaw, stamp, status = valid_camera_sample(camera.read(), now) if camera else (None, None, 0, 'Camera disabled')
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mapped = canvas_point(event.pos, screen.get_size())
                    if calibration_dialog:
                        if calibrate_button.collidepoint(mapped):
                            pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_c))
                        elif skip_button.collidepoint(mapped):
                            calibration_dialog = False
                            calibrating = False
                            emit('Initial calibration skipped; monitoring needs calibration')
                        continue
                    if started and change_button.collidepoint(mapped):
                        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
                    elif not started:
                        for index, button in enumerate(scenario_buttons):
                            if button.collidepoint(mapped):
                                selected_scenario = scenario_names[index]
                                car = Driving(emit, selected_scenario, settings)
                                emit('Scenario selected: '+selected_scenario)
                                emit('Configuration: '+json.dumps(settings[selected_scenario]))
                        if start_button.collidepoint(mapped):
                            started = True
                            emit('Drive started in selected lane')
                if event.type == pygame.MOUSEWHEEL:
                    log_scroll = max(0, log_scroll+event.y*3)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F9:
                        demo_view = not demo_view
                        continue
                    if event.key == pygame.K_F11:
                        fullscreen = not fullscreen
                        screen = pygame.display.set_mode((0,0),pygame.FULLSCREEN) if fullscreen else pygame.display.set_mode((1440,850),pygame.RESIZABLE)
                        continue
                    if calibration_dialog and event.key == pygame.K_k:
                        calibration_dialog = False
                        calibrating = False
                        emit('Initial calibration skipped; monitoring needs calibration')
                        continue
                    if calibration_dialog and event.key not in (pygame.K_c,pygame.K_ESCAPE):
                        continue
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
                    elif event.key == pygame.K_p and speech:
                        if speech.spotify_enabled.is_set():
                            speech.spotify_enabled.clear()
                        else:
                            speech.spotify_enabled.set()
                        emit('Other audio speech priority '+('enabled' if speech.spotify_enabled.is_set() else 'disabled'))
                    elif event.key == pygame.K_t and speech:
                        speech.say({'tunnel':'Take control. Automation ends at tunnel.','obstacle':'Obstruction ahead. Slow down and take control.','rain':'Take control. Visibility is below the operating limit.'}[selected_scenario])
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
                        calibration_dialog = False
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

            score = yaw[2] if yaw is not None else float('nan')
            closed_for = 0 if monitor.closed_since is None else now-monitor.closed_since
            speech_active = bool(speech and speech.busy.is_set())
            priority_enabled = bool(speech and speech.spotify_enabled.is_set())
            audio_status = 'Demo audio off'
            if speech_active:
                audio_status = 'Speech prioritised'
            elif music_enabled:
                audio_status = 'Demo audio paused' if audio_paused else 'Demo audio playing'
            log_scroll = draw_dashboard(
                canvas, car, now=now, camera_view=(frame, status),
                monitoring=(state, eyes, relative, score, closed_for, calibration_note),
                audio=(audio_status, priority_enabled), history=history, scroll=log_scroll,
                keys=keys, flashes=flashes, started=started, change_button=change_button,
                scenario_buttons=scenario_buttons, start_button=start_button,
                calibration_dialog=calibration_dialog, calibrate_button=calibrate_button,
                skip_button=skip_button, demo_view=demo_view,
            )
            viewport = fit_view(screen.get_size())
            screen.fill('#090f15')
            image = canvas if viewport.size == CANVAS_SIZE else pygame.transform.smoothscale(canvas, viewport.size)
            screen.blit(image, viewport.topleft)
            pygame.display.flip()
            frames += 1
            if args.smoke:
                pygame.image.save(canvas,str(ROOT / f'evidence/gui-review-{selected_scenario}-{frames}.png'))
                started = True
                calibration_dialog = False
                if frames == 1:
                    car.distance = car.boundary
                    if selected_scenario == 'rain':
                        car.rain_started = car.elapsed-9
                        car.event_started = True
                if frames == 2:
                    car.mode = 'Automated driving'
                    car.request('Visibility is below the operating limit.' if selected_scenario == 'rain' else 'Obstruction ahead. Slow down.' if selected_scenario == 'obstacle' else 'Automation ends at tunnel.')
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
            speech.thread.join(timeout=5)
        if not args.smoke:
            folder = ROOT / 'evidence/runs'
            folder.mkdir(exist_ok=True)
            (folder / (str(time.time_ns()) + '.json')).write_text(json.dumps(records, indent=2))
        pygame.quit()


if __name__ == '__main__':
    main()

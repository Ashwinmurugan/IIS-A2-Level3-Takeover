"""Iteration 1: local webcam, keyboard driving and speech feasibility."""
import argparse
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
                num_faces=1, output_facial_transformation_matrixes=True)
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
                        yaw = math.degrees(math.atan2(rotation[0, 2], rotation[2, 2]))
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
        self.requests = queue.Queue(maxsize=1)
        self.busy = threading.Event()
        self.events = events
        threading.Thread(target=self.run, daemon=True).start()

    def say(self):
        if self.busy.is_set():
            return
        self.busy.set()
        self.requests.put_nowait('Take control. Automated driving ends at the tunnel.')

    def run(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 165)
            while True:
                message = self.requests.get()
                self.events.put('Speech playback started')
                engine.say(message)
                engine.runAndWait()
                self.events.put('Speech playback completed')
                self.busy.clear()
        except Exception as error:
            self.events.put('Speech unavailable: ' + str(error))
            self.busy.set()


def advance(speed, position, distance, throttle, steer, dt):
    speed = float(np.clip(speed + throttle * 18 * dt, 0, 100))
    position = float(np.clip(position + steer * speed / 100 * dt, -1.3, 1.3))
    return speed, position, distance + speed / 3.6 * dt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera', type=int, default=0)
    parser.add_argument('--no-camera', action='store_true')
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if args.smoke:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
    pygame.init()
    screen = pygame.display.set_mode((1440, 850), pygame.RESIZABLE)
    pygame.display.set_caption('IIS A2 - Iteration 1 feasibility')
    canvas = pygame.Surface((1440, 850))
    font = pygame.font.SysFont('Segoe UI', 20)
    small = pygame.font.SysFont('Segoe UI', 17)
    heading = pygame.font.SysFont('Segoe UI', 28, bold=True)
    events = queue.Queue()
    speech = None if args.smoke else Speech(events)
    camera = None if args.smoke or args.no_camera else Camera(args.camera)
    history = deque(maxlen=10)
    samples = deque()
    baseline = None
    calibrating = False
    calibrated_at = 0.0
    speed, position, distance = 45.0, 0.0, 0.0
    manual = True
    clock = pygame.time.Clock()
    start = time.monotonic()
    previous_state = ''
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
                y += 22
                line = word
            else:
                line = candidate
        text(line, x, y, color, small)
        return y + 26

    log('Practice mode started')
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
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_c:
                        samples.clear()
                        calibrating, calibrated_at = True, now
                        baseline = None
                        log('Calibration requested; face forward')
                    elif event.key == pygame.K_t and speech:
                        speech.say()
                    elif event.key == pygame.K_SPACE:
                        manual = True
                        log('Manual control selected')
                    elif event.key == pygame.K_f:
                        manual, position = False, 0.0
                        log('Simulated lane following selected')
                    elif event.key == pygame.K_r:
                        speed, position, distance, manual = 45.0, 0.0, 0.0, True
                        log('Practice road reset')
            if calibrating:
                if yaw is not None and stamp != last_sample:
                    samples.append(yaw)
                    last_sample = stamp
                if now - calibrated_at >= 2:
                    calibrating = False
                    if len(samples) >= 12 and np.std(samples) < 5:
                        baseline = float(np.median(samples))
                        log('Forward position calibrated')
                    else:
                        log('Calibration failed; hold still and retry C')
            relative = None if yaw is None or baseline is None else (yaw - baseline + 180) % 360 - 180
            state = 'Unavailable' if yaw is None else 'Needs calibration'
            if relative is not None:
                state = 'Turned away' if abs(relative) > 25 else 'Facing forward'
            if state != previous_state:
                previous_state, state_since = state, now
                log('Head cue: ' + state)
            while not events.empty():
                log(events.get_nowait())
            keys = pygame.key.get_pressed()
            throttle = int(keys[pygame.K_w]) - int(keys[pygame.K_s]) if manual else 0
            steer = int(keys[pygame.K_d]) - int(keys[pygame.K_a]) if manual else 0
            speed, position, distance = advance(speed, position, distance, throttle, steer, dt)

            canvas.fill(BG)
            text('LEVEL 3 / TAKEOVER INTERFACE', 24, 18, face=heading)
            text('Iteration 1  /  Camera, driving and speech feasibility', 24, 55, MUTED)
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
            text('Relative yaw: ' + ('--' if relative is None else f'{relative:+.1f} degrees'), 32, 430)
            text(f'Current cue: {now - state_since:.1f}s', 32, 464, MUTED)
            wrap('Calibrating: hold forward...' if calibrating else 'C  Calibrate while facing the screen', 32, 515, 270)
            wrap('Head orientation is an experimental cue. Camera frames stay local and are not recorded.', 32, 595, 265)
            text('PRACTICE ROAD', 354, 118, TEAL)
            pygame.draw.rect(canvas, '#647b89', (354, 160, 688, 330))
            pygame.draw.polygon(canvas, '#344e45', [(354, 260), (1042, 260), (1042, 490), (354, 490)])
            center = 698 - position * 120
            pygame.draw.polygon(canvas, '#333b46', [(678, 260), (718, 260), (center + 300, 490), (center - 300, 490)])
            for i in range(12):
                depth = ((i / 12 + distance / 150) % 1) ** 2
                y = 260 + depth * 230
                x = 698 + (center - 698) * depth
                pygame.draw.line(canvas, '#f0ede0', (x, y), (x, y + 5 + depth * 12), max(1, int(depth * 5)))
            text(f'{speed:05.1f} km/h', 380, 520, face=heading)
            text('MANUAL CONTROL' if manual else 'AUTOMATION ACTIVE', 680, 526, TEAL)
            text(f'Distance travelled  {distance:.0f} m', 380, 568, MUTED)
            text('Lane offset  ' + f'{position:+.2f}', 680, 568, AMBER if abs(position) > .8 else MUTED)
            wheel = (690, 650)
            pygame.draw.circle(canvas, '#91a3b2', wheel, 45, 5)
            angle = steer * .65
            dx, dy = math.cos(angle) * 39, math.sin(angle) * 39
            pygame.draw.line(canvas, WHITE, (690-dx, 650-dy), (690+dx, 650+dy), 5)
            text('T  Play sample takeover speech', 380, 717)
            text('LIVE EVENT LOG', 1092, 118, TEAL)
            y = 165
            for elapsed, message in list(history)[-6:]:
                text(f'{elapsed:06.1f}s', 1092, y, TEAL, small)
                y = wrap(message, 1092, y + 21, 308) + 5
                if y > 704:
                    break
            text('W/S speed   A/D steer   SPACE manual   F automation   R reset   C calibrate   ESC exit', 24, 793)
            text('Feasibility build. Full warning sequence, haptics indicators and media priority are pending.', 24, 823, MUTED, small)
            screen.blit(pygame.transform.smoothscale(canvas, screen.get_size()), (0, 0))
            pygame.display.flip()
            frames += 1
            if args.smoke and frames == 3:
                pygame.image.save(canvas, str(ROOT / 'evidence/feasibility-smoke.png'))
                print('PASS: application rendered 3 frames without camera or speech')
                running = False
    finally:
        if camera:
            camera.close()
        pygame.quit()


if __name__ == '__main__':
    main()

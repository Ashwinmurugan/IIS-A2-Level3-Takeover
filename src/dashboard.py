"""Presentation for the simulator. Reads state without changing driving rules."""
from functools import lru_cache
import math

import pygame

from scene import draw_log, draw_road


CANVAS_SIZE = (1440, 850)
BACKGROUND = '#0b1118'
PANEL = '#141e29'
INSET = '#0e1720'
BORDER = '#2b3c4c'
WHITE = '#ecf3fa'
MUTED = '#a7b8c9'
TEAL = '#60dfca'
AMBER = '#ffca75'
RED = '#ff8580'

SCENARIO_LABELS = {'tunnel': 'Tunnel', 'obstacle': 'Road obstruction', 'rain': 'Heavy rain'}
CONTROLS = (
    (pygame.K_w, 'W', 'Accelerate'), (pygame.K_s, 'S', 'Brake'),
    (pygame.K_a, 'A', 'Steer left'), (pygame.K_d, 'D', 'Steer right'),
    (pygame.K_q, 'Q', 'Signal left'), (pygame.K_e, 'E', 'Signal right'),
    (pygame.K_f, 'F', 'Auto drive'), (pygame.K_SPACE, 'Space', 'Take over'),
    (pygame.K_r, 'R', 'Restart'), (pygame.K_c, 'C', 'Calibrate'),
    (pygame.K_m, 'M', 'Demo audio'), (pygame.K_t, 'T', 'Test speech'),
    (pygame.K_ESCAPE, 'Esc', 'Exit'),
)


def fit_view(size):
    """Centre the display at its native aspect ratio, including on wide monitors."""
    scale = min(size[0] / CANVAS_SIZE[0], size[1] / CANVAS_SIZE[1])
    rect = pygame.Rect(0, 0, *(max(1, round(axis * scale)) for axis in CANVAS_SIZE))
    rect.center = size[0] // 2, size[1] // 2
    return rect


def canvas_point(position, size):
    rect = fit_view(size)
    return ((position[0] - rect.x) * CANVAS_SIZE[0] / rect.w,
            (position[1] - rect.y) * CANVAS_SIZE[1] / rect.h)


@lru_cache(maxsize=24)
def font(size, bold=False):
    return pygame.font.SysFont('Segoe UI', size, bold=bold)


def label(surface, value, x, y, *, size=20, color=WHITE, bold=False):
    surface.blit(font(size, bold).render(value, True, color), (x, y))


def fitted_label(surface, value, x, y, width, *, size=20, color=WHITE, bold=False):
    """Keep variable status text within its allotted instrument area."""
    while size > 14 and font(size, bold).size(value)[0] > width:
        size -= 1
    label(surface, value, x, y, size=size, color=color, bold=bold)


def paragraph(surface, value, x, y, width, *, size=18, color=MUTED):
    face = font(size)
    line = ''
    for word in value.split():
        candidate = f'{line} {word}'.strip()
        if line and face.size(candidate)[0] > width:
            label(surface, line, x, y, size=size, color=color)
            y += face.get_linesize() + 3
            line = word
        else:
            line = candidate
    if line:
        label(surface, line, x, y, size=size, color=color)


def frame(surface, rect, fill=PANEL, edge=BORDER, radius=12):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, edge, rect, width=1, border_radius=radius)
    bounds = pygame.Rect(rect)
    if bounds.height > 80:
        highlight = pygame.Color(fill).lerp(pygame.Color('#70849a'), .12)
        pygame.draw.line(surface, highlight, (bounds.left+radius, bounds.top+1),
                         (bounds.right-radius, bounds.top+1))


def button(surface, rect, value, selected=False):
    frame(surface, rect, TEAL if selected else '#21313f', TEAL if selected else BORDER, 8)
    rendered = font(20, True).render(value, True, BACKGROUND if selected else WHITE)
    surface.blit(rendered, rendered.get_rect(center=rect.center))


def draw_monitor(surface, preview, status, head, eyes, angles, closure, closed_for, calibration):
    label(surface, 'DRIVER MONITORING', 34, 114, size=19, bold=True)
    camera_view = pygame.Rect(32, 151, 274, 206)
    frame(surface, camera_view, INSET, radius=8)
    if preview is not None:
        image = pygame.image.frombuffer(preview.tobytes(), (preview.shape[1], preview.shape[0]), 'RGB')
        image = pygame.transform.scale(pygame.transform.flip(image, True, False), camera_view.size)
        surface.blit(image, camera_view)
    else:
        paragraph(surface, status, 50, 235, 234)
    preview_color = TEAL if preview is not None else MUTED
    preview_label = 'CAMERA FEED' if preview is not None else 'NO CAMERA FEED'
    frame(surface, (42, 162, 143, 25), INSET, BORDER, 5)
    pygame.draw.circle(surface, preview_color, (53, 174), 3)
    label(surface, preview_label, 63, 166, size=13, color=preview_color, bold=True)
    for x, direction_x in ((42,1),(296,-1)):
        for y, direction_y in ((154,1),(347,-1)):
            pygame.draw.lines(surface, preview_color, False,
                              [(x,y+direction_y*10),(x,y),(x+direction_x*10,y)], 2)

    head_color = TEAL if head == 'Facing forward' else AMBER
    eye_color = AMBER if eyes == 'Eyes appear closed' else TEAL if eyes == 'Open estimate' else MUTED
    for top, caption, value, color in (
        (373, 'HEAD DIRECTION', 'Tracking unavailable' if head == 'Unavailable' else head, head_color),
        (453, 'EYE CLOSURE', 'Estimate unavailable' if eyes == 'Unknown' else eyes, eye_color),
    ):
        frame(surface, (32, top, 274, 69), INSET, radius=8)
        pygame.draw.rect(surface, color, (32, top+14, 3, 40), border_radius=2)
        label(surface, caption, 46, top+10, size=15, color=MUTED, bold=True)
        fitted_label(surface, value, 46, top+30, 248, size=22, color=color, bold=True)

    label(surface, 'TRACKING DETAILS', 34, 540, size=15, color=MUTED, bold=True)
    pose = '— / —' if angles is None else f'{angles[0]:+.0f}° / {angles[1]:+.0f}°'
    label(surface, f'Yaw / pitch   {pose}', 34, 567, size=19)
    eye_value = f'{closure:.2f} · {closed_for:.1f} s' if math.isfinite(closure) else '—'
    label(surface, f'Closure score   {eye_value}', 34, 598, size=19)
    pygame.draw.line(surface, BORDER, (34, 637), (292, 637))
    paragraph(surface, calibration, 34, 650, 258, size=18, color=TEAL)
    paragraph(surface, 'C sets your forward reference. Camera frames stay on this PC.', 34, 709, 255, size=17)


def draw_alert(surface, car, now):
    notice_active = now < car.notice_until and bool(car.notice)
    denied = notice_active and 'unavailable' in car.notice.lower()
    active = car.stage > 0 or denied
    color = RED if car.stage >= 2 else AMBER if active else TEAL
    fill = '#321d24' if car.stage >= 2 else '#30251b' if active else '#13272b'
    frame(surface, (338, 149, 740, 84), fill, color, 9)
    pygame.draw.rect(surface, color, (343, 158, 3, 66), border_radius=2)
    if active:
        pygame.draw.polygon(surface, color, [(372, 166), (350, 211), (395, 211)])
        label(surface, '!', 368, 176, size=24, color=BACKGROUND, bold=True)
    else:
        pygame.draw.circle(surface, color, (373, 190), 13, 2)
        pygame.draw.circle(surface, color, (373, 190), 4)

    title = {1: 'TAKE CONTROL', 2: 'TAKE CONTROL NOW', 3: 'SLOWING AUTOMATICALLY',
             4: 'EMERGENCY BRAKING'}.get(car.stage, car.mode)
    detail = car.message
    show_takeover_key = car.stage in (1, 2) and not denied and not car.collision
    if car.stage in (1, 2):
        detail = car.reason
    elif car.stage == 4:
        detail = 'Braking active · preparing to stop'
    if notice_active and not car.stage:
        detail = car.notice
    if car.mode == 'Automatic slowing':
        detail = 'No takeover confirmed. Press Space to take over.'
    if car.mode == 'Stopped':
        title, detail = 'VEHICLE STOPPED', car.stop_reason
    if car.collision:
        title, detail = 'COLLISION RECORDED', 'Stopping margin insufficient. Press R to restart.'
    if denied:
        title = 'AUTOMATION UNAVAILABLE'
    fitted_label(surface, title, 410, 158, 530 if show_takeover_key else 650,
                 size=37 if active else 32, color=color if active else WHITE, bold=True)
    paragraph(surface, detail, 411, 199, 522 if show_takeover_key else 650, color=WHITE, size=18)
    if show_takeover_key:
        frame(surface, (951, 167, 108, 46), color, color, 7)
        label(surface, 'Press Space', 962, 179, size=17, color=BACKGROUND, bold=True)


def draw_instruments(surface, car, now, audio_label, priority_enabled):
    frame(surface, (338, 566, 740, 193), '#1a242d', '#43515e')
    frame(surface, (347, 575, 722, 141), '#101921', '#263746', 8)
    pygame.draw.line(surface, '#283b48', (578, 590), (578, 697))
    pygame.draw.line(surface, '#283b48', (835, 590), (835, 697))
    label(surface, 'SPEED', 363, 588, size=15, color=MUTED, bold=True)
    speed = f'{car.speed:.0f}'
    label(surface, speed, 359, 602, size=65, bold=True)
    label(surface, 'km/h', 370 + font(65, True).size(speed)[0], 643, size=18, color=MUTED)
    label(surface, f'{car.distance:.0f} m travelled', 363, 682, size=17, color=MUTED)
    # An unnumbered speed strip is a supplementary cue, not a speed-limit claim.
    for index in range(24):
        lit = index < round(min(1, max(0, car.speed)/140)*24)
        pygame.draw.rect(surface, TEAL if lit else '#293b49',
                         (363+index*8, 672, 5, 3), border_radius=1)

    centre = (707, 647)
    rotation = car.steer * .65
    pygame.draw.circle(surface, '#080e14', (centre[0],centre[1]+3), 48)
    pygame.draw.circle(surface, '#526678', centre, 45, 8)
    pygame.draw.arc(surface, '#a6bccb', (662,602,90,90), .25, math.pi-.25, 2)
    pygame.draw.circle(surface, '#243643', centre, 38, 2)
    for spoke in (0, math.pi, math.pi/2):
        angle = spoke + rotation
        tip = (centre[0]+math.cos(angle)*39, centre[1]+math.sin(angle)*39)
        pygame.draw.line(surface, '#536d7d', centre, tip, 9)
    pygame.draw.circle(surface, '#1b2c38', centre, 16)
    pygame.draw.circle(surface, '#7c95a6', centre, 16, 2)
    pygame.draw.line(surface, '#92a8b7', (700,644), (714,644), 2)
    pygame.draw.line(surface, '#92a8b7', (703,649), (711,649), 2)
    mark = rotation - math.pi/2
    inner = (centre[0]+math.cos(mark)*37, centre[1]+math.sin(mark)*37)
    outer = (centre[0]+math.cos(mark)*45, centre[1]+math.sin(mark)*45)
    pygame.draw.line(surface, TEAL, inner, outer, 3)
    blink = int(now * 2) % 2 == 0
    for direction in (-1, 1):
        x = centre[0] + direction*83
        points = ((0,-13),(16,0),(0,13),(0,6),(-15,6),(-15,-6),(0,-6))
        lit = blink and (car.hazards or car.signal == direction)
        pygame.draw.polygon(surface, AMBER if lit else '#374858', [(x+a*direction,648+b) for a,b in points])
    steering_label = 'Hazard lights active' if car.hazards else 'Steering'
    steering_color = AMBER if car.hazards else MUTED
    x = centre[0] - font(15, True).size(steering_label)[0]//2
    label(surface, steering_label, x, 695, size=15, color=steering_color, bold=True)

    label(surface, 'CONTROL MODE', 854, 588, size=15, color=MUTED, bold=True)
    mode_color = RED if car.stage >= 3 else AMBER if car.stage else TEAL
    fitted_label(surface, car.mode, 854, 613, 201, size=21, color=mode_color, bold=True)
    label(surface, f'Lane {car.lane+1}', 854, 649, size=20)
    label(surface, f'Offset {car.position-car.lane:+.2f}', 854, 678, size=17, color=MUTED)

    pygame.draw.line(surface, BORDER, (352, 716), (1064, 716))
    vibration = car.stage >= 2
    vibration_color = AMBER if vibration else MUTED
    pygame.draw.lines(surface, vibration_color, False, [(358,731),(361,739),(368,739),(371,743)], 2)
    pygame.draw.circle(surface, vibration_color, (382,737), 6, 2)
    pygame.draw.line(surface, vibration_color, (377,737), (387,737), 2)
    label(surface, 'Simulated vibration ' + ('active' if vibration else 'inactive'), 394, 729,
          size=15, color=vibration_color, bold=vibration)
    label(surface, audio_label, 585, 729, size=16, color=WHITE)
    label(surface, 'P · Audio priority ' + ('on' if priority_enabled else 'off'), 856, 729, size=16, color=MUTED)


def draw_scenario_icon(surface, scenario, x, y, color):
    if scenario == 'tunnel':
        pygame.draw.arc(surface, color, (x-10,y-10,20,21), 0, math.pi, 2)
        pygame.draw.lines(surface, color, False, [(x-10,y),(x-10,y+9),(x+10,y+9),(x+10,y)], 2)
        pygame.draw.line(surface, color, (x,y+4), (x,y+9), 2)
    elif scenario == 'obstacle':
        pygame.draw.polygon(surface, color, [(x,y-11),(x-11,y+9),(x+11,y+9)], 2)
        pygame.draw.line(surface, color, (x,y-4), (x,y+2), 2)
        pygame.draw.circle(surface, color, (x,y+5), 1)
    else:
        for dx, dy in ((-5,0),(1,-4),(7,0)):
            pygame.draw.circle(surface, color, (x+dx,y-3+dy), 5)
        for dx in (-6,0,6):
            pygame.draw.line(surface, color, (x+dx,y+4), (x+dx-2,y+9), 2)


def draw_setup(surface, car, buttons, action):
    frame(surface, (349, 245, 718, 324), '#142331', '#3c556a', 14)
    label(surface, 'Choose a scenario', 371, 258, size=28, bold=True)
    for index, (scenario, rect) in enumerate(zip(SCENARIO_LABELS, buttons), start=1):
        selected = car.scenario == scenario
        frame(surface, rect, '#20413f' if selected else '#192b3b', TEAL if selected else BORDER, 8)
        accent = TEAL if selected else MUTED
        draw_scenario_icon(surface, scenario, rect.x+20, rect.centery, accent)
        label(surface, SCENARIO_LABELS[scenario], rect.x+38, rect.y+14, size=16, bold=True)
        frame(surface, (rect.right-26, rect.y+13, 20, 22), INSET, BORDER, 4)
        label(surface, str(index), rect.right-20, rect.y+16, size=13, color=accent, bold=True)
    label(surface, 'C  Set your forward camera reference', 371, 367, color=WHITE)
    label(surface, f'Start at {car.speed:.0f} km/h · Lane {car.lane+1}', 371, 404, size=18, color=MUTED)
    label(surface, 'Space takes over during a drive. Tab returns here.', 371, 439, size=18, color=MUTED)
    button(surface, action, 'Start drive  /  Enter', True)


def draw_calibration(surface, calibration, calibrate, skip):
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((4, 9, 13, 218))
    surface.blit(shade, (0, 0))
    frame(surface, (365, 240, 710, 348), '#172534', '#4a677c', 16)
    label(surface, 'Calibrate your camera', 405, 269, size=33, bold=True)
    paragraph(surface, 'Set a forward reference so the simulator can estimate when your head turns away.',
              405, 326, 610, size=20, color=WHITE)
    label(surface, 'Face the road view, keep your eyes open and hold for two seconds.', 405, 383, size=18, color=MUTED)
    label(surface, calibration, 405, 421, size=18, color=TEAL)
    button(surface, calibrate, 'Calibrate  /  C', True)
    button(surface, skip, 'Skip for now  /  K')
    label(surface, 'C recalibrates during the drive. F11 toggles full screen.', 405, 550, size=18, color=MUTED)


def draw_dashboard(surface, car, *, now, camera_view, monitoring, audio, history, scroll,
                   keys, flashes, started, change_button, scenario_buttons, start_button,
                   calibration_dialog, calibrate_button, skip_button):
    surface.fill(BACKGROUND)
    pygame.draw.line(surface, BORDER, (16, 84), (1424, 84))
    pygame.draw.rect(surface, TEAL, (23, 21, 4, 49), border_radius=2)
    label(surface, 'Level 3 Takeover Simulator', 40, 17, size=33, bold=True)
    label(surface, 'Desktop driving simulation   ·   F11 full screen', 41, 57, size=17, color=MUTED)
    if started:
        button(surface, change_button, 'Change scenario  /  Tab')
    for rect in ((16, 96, 304, 675), (326, 96, 764, 675), (1096, 96, 328, 675)):
        frame(surface, rect)
    draw_monitor(surface, *camera_view, *monitoring)
    label(surface, SCENARIO_LABELS[car.scenario].upper(), 340, 113, size=20, bold=True)
    location = car.location_label
    label(surface, location, 1078 - font(18).size(location)[0], 115, size=18, color=MUTED)
    draw_road(surface, car, pygame.Rect(338, 241, 740, 321))
    draw_alert(surface, car, now)
    draw_instruments(surface, car, now, *audio)
    label(surface, 'EVENT LOG', 1110, 112, size=20, bold=True)
    scroll = draw_log(surface, history, font(19, True), scroll)

    for index, (code, key, action) in enumerate(CONTROLS):
        x = 16 + index*109
        pressed = keys[code] or flashes.get(code, 0) > now
        frame(surface, (x, 780, 100, 60), '#153b3b' if pressed else INSET, TEAL if pressed else BORDER, 8)
        label(surface, key, x+9, 786, size=20, bold=True, color=TEAL if pressed else WHITE)
        label(surface, action, x+9, 814, size=15, color=MUTED)
    if not started:
        draw_setup(surface, car, scenario_buttons, start_button)
    if calibration_dialog:
        draw_calibration(surface, monitoring[-1], calibrate_button, skip_button)
    return scroll

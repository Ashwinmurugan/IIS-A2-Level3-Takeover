"""Road illustration and observer log. All inputs come from the simulator."""
from functools import lru_cache
import math

import pygame


@lru_cache(maxsize=24)
def sky(size, storm_level):
    surface = pygame.Surface(size)
    storm = storm_level / 20
    top = pygame.Color('#426c8a').lerp(pygame.Color('#25323f'), storm)
    base = pygame.Color('#c2d3d6').lerp(pygame.Color('#899ba5'), storm)
    for y in range(size[1]):
        color = top.lerp(base, y / max(1, size[1]-1))
        pygame.draw.line(surface, color, (0, y), (size[0], y))
    clouds = pygame.Surface(size, pygame.SRCALPHA)
    tint = pygame.Color(238,244,240,41).lerp(pygame.Color(33,45,56,25), storm)
    for index in range(6):
        x = (index*193 + 32) % size[0]
        y = 8 + (index*19) % 66
        width = 95 + index*11
        pygame.draw.ellipse(clouds, tint, (x-70,y,width,21))
    surface.blit(clouds,(0,0))
    return surface


def arch(x, bottom, half_width, height):
    return [(x-half_width, bottom), *(
        (x+math.cos(math.pi*(12-i)/12)*half_width,
         bottom-height*(.32+.68*math.sin(math.pi*(12-i)/12)))
        for i in range(13)), (x+half_width, bottom)]


@lru_cache(maxsize=24)
def mist(size, strength):
    """Rain haze is strongest at the horizon and fades in the foreground."""
    layer = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(size[1]):
        depth_fade = math.exp(-((y-95)/82)**2)
        alpha = round(strength*(28+114*depth_fade)/20)
        pygame.draw.line(layer, (157,178,190,alpha), (0,y), (size[0],y))
    return layer


def draw_rain(canvas, viewport, intensity, elapsed):
    width, height = viewport.size
    canvas.blit(mist(viewport.size,round(intensity*20)),viewport.topleft)
    rain = pygame.Surface(viewport.size, pygame.SRCALPHA)
    # Different speeds and lengths give the rain depth without covering the HUD.
    layers = (
        (76, 305, 4, 13, 82, 1),
        (27, 540, 9, 26, 114, 2),
    )
    for spacing, fall_speed, tilt, length, opacity, weight in layers:
        for index in range(round(spacing*intensity)):
            x = (index*97.53 + elapsed*76) % (width+tilt)
            y = (index*52.27 + elapsed*fall_speed) % (height+length) - length
            pygame.draw.line(rain,(211,232,243,opacity),(x,y),(x-tilt,y+length),weight)
    canvas.blit(rain,viewport.topleft)


def draw_road(canvas, car, viewport):
    previous_clip = canvas.get_clip()
    canvas.set_clip(viewport)
    horizon = viewport.top + 95
    vanishing_x = viewport.centerx
    ground = viewport.bottom
    gap = car.boundary - car.distance
    tunnel = car.scenario == 'tunnel'
    inside = tunnel and -car.tunnel_length < gap <= 0
    rain_intensity = car.rain_intensity if car.scenario == 'rain' else 0
    storm = rain_intensity > 0

    def project(lateral, depth):
        perspective = 7 + 241*depth
        return (vanishing_x + (lateral-car.position)*perspective,
                horizon+(ground-horizon)*depth)

    def band(left, right, color, start=0, end=1):
        pygame.draw.polygon(canvas, color, [project(left,start), project(right,start),
                                            project(right,end), project(left,end)])

    if inside:
        canvas.fill('#171d25', viewport)
        for side, color in ((-1,'#2b353d'),(1,'#222c35')):
            wall = viewport.left if side < 0 else viewport.right
            pygame.draw.polygon(canvas,color,[(wall,viewport.top),(vanishing_x,horizon-34),
                                               (vanishing_x,horizon+8),(wall,ground)])
        for index in range(8):
            depth = ((index/8 + car.distance/135) % 1)**2
            x, y = project(.5,depth)
            pygame.draw.lines(canvas,'#39434b',False,arch(x,y,19+depth*344,22+depth*330),max(1,round(3*depth)))
        exit_depth = 37/(37+car.tunnel_length+gap)
        x, y = project(.5, exit_depth)
        width, height = 10+exit_depth*265, 22+exit_depth*330
        pygame.draw.polygon(canvas,'#738f9b',arch(x,y,width+5,height+5))
        pygame.draw.polygon(canvas,'#c2d8dd',arch(x,y,width,height))
    else:
        canvas.blit(sky(viewport.size,round(rain_intensity*20)),viewport.topleft)
        hills = [(viewport.left,horizon+15)]
        for step in range(21):
            x = viewport.left + step*viewport.width/20
            height = 5+21*abs(math.sin(step*.46-2.1))
            hills.append((x,horizon-height))
        hills.append((viewport.right,horizon+15))
        pygame.draw.polygon(canvas,'#536b72',hills)
        canvas.fill('#354d44', (viewport.left,horizon+5,viewport.width,ground-horizon))
        if tunnel and gap > 0:
            depth = 43/(43+gap)
            x, bottom = project(.5, depth)
            width = 11+depth*300
            height = 20+depth*390
            pygame.draw.polygon(canvas, '#92a1a6', arch(x,bottom,width,height))
            pygame.draw.polygon(canvas, '#53636b', arch(x,bottom,width*.88,height*.91))
            pygame.draw.polygon(canvas, '#1a2129', arch(x,bottom,width*.75,height*.80))

    band(-.67,1.67,'#596671' if inside else '#747b76')
    road_color = pygame.Color('#353f49').lerp(pygame.Color('#283641'), rain_intensity)
    band(-.5,1.5,road_color)
    if storm:
        # Narrow, low-contrast streaks suggest wet asphalt rather than paving tiles.
        for index in range(32):
            depth = ((index/32 + car.distance/105) % 1)**2
            lateral = -.43+(index*0.427) % 1.80
            color = road_color.lerp(pygame.Color('#627988'), rain_intensity*depth*.19)
            band(lateral,lateral+.035,color,depth,min(1,depth+.08))
    if tunnel and not inside and gap > 0:
        depth = 43/(43+gap)
        band(-.50,1.50,road_color.lerp(pygame.Color('#101820'),.42),depth,min(1,depth+.06))
    if inside:
        for index in range(6):
            depth = ((index/6 + car.distance/125) % 1)**2
            # Soft light pools keep the lane markings visually dominant.
            for edge in range(5):
                start = depth + edge*.006
                strength = (.035+.09*depth)*(1-abs(edge-2)/3)
                color = road_color.lerp(pygame.Color('#b6a277'),strength)
                band(-.48,1.48,color,start,min(1,start+.012))
    band(-.49,-.465,'#dbe2db')
    band(1.465,1.49,'#dbe2db')
    if not inside:
        # Perspective rails provide lateral motion cues without covering the road.
        for side in (-.88, 1.88):
            for lift, color in ((12, '#52635f'), (17, '#a0aaa5')):
                points = []
                for depth in (0, .15, .4, .7, 1):
                    x, y = project(side, depth)
                    points.append((x, y-lift*depth))
                pygame.draw.lines(canvas, color, False, points, 2)
    for index in range(13):
        offset = (index/13 + car.distance/105) % 1
        band(.489,.511,'#e0e6e1',offset**2,min(1,offset+.032)**2)

    markers = 8
    for index in range(markers):
        depth = ((index/markers + car.distance/135) % 1)**2
        for side in (-.77, 1.77):
            x, y = project(side, depth)
            if inside:
                lamp_y = y-15-160*depth
                pygame.draw.line(canvas, '#685f50', (x-14*depth,lamp_y), (x+14*depth,lamp_y), 4+round(5*depth))
                pygame.draw.line(canvas, '#f7deaa', (x-9*depth,lamp_y), (x+9*depth,lamp_y), 2+round(2*depth))
            else:
                tip = y-3-27*depth
                pygame.draw.line(canvas, '#aab8b3', (x,y), (x,tip), max(1,round(4*depth)))
                if depth > .12:
                    pygame.draw.circle(canvas,'#dae1d9',(x,tip+2),max(1,round(3*depth)))

    if car.scenario == 'obstacle' and car.event_started and car.gap > -5:
        depth = 40/(max(0, car.gap)+40)
        x, y = project(car.config['obstacle_lane'], depth)
        width = 20 + depth*118
        pygame.draw.ellipse(canvas,'#1b2329',(x-width*.67,y-width*.09,width*1.34,width*.19))
        for side in (-1,1):
            pygame.draw.rect(canvas,'#171d22',(x+side*width*.36-width*.08,y-width*.25,width*.16,width*.26),border_radius=2)
        bumper = pygame.Rect(x-width/2,y-width*.62,width,width*.62)
        pygame.draw.rect(canvas, '#101a21', bumper.inflate(7,5), border_radius=6)
        pygame.draw.rect(canvas, '#a7504b', bumper, border_radius=5)
        pygame.draw.line(canvas,'#d48678',bumper.topleft,bumper.topright,max(1,int(width*.035)))
        pygame.draw.polygon(canvas,'#91adbe',[(x-width*.35,y-width*.36),(x-width*.23,y-width*.54),
                                              (x+width*.23,y-width*.54),(x+width*.35,y-width*.36)])
        pygame.draw.rect(canvas, '#d4bf87', (x-width*.14,y-width*.18,width*.28,max(2,width*.08)), border_radius=2)
        for side in (-1, 1):
            pygame.draw.circle(canvas, '#ffab63', (x+side*width*.36,y-width*.13), max(2,int(width*.06)))
        size = max(7,width*.16)
        triangle_x = x + width*.65
        pygame.draw.polygon(canvas, '#ffbc70', [(triangle_x,y-size*1.5),(triangle_x-size,y),(triangle_x+size,y)], 2)
    if storm:
        draw_rain(canvas,viewport,rain_intensity,car.elapsed)
    canvas.set_clip(previous_clip)
    pygame.draw.rect(canvas, '#354857', viewport, width=1)


def log_rows(history, font):
    rows = []
    for index, (elapsed, message) in enumerate(history):
        lower = message.lower()
        category, color = 'OBSERVATION', '#a7b8c9'
        if any(word in lower for word in ('warning','unavailable','deadline','attention','hazard',
                                           'rejected','takeover requested','collision','emergency')):
            category, color = 'ALERT', '#ffca75'
        elif not lower.startswith(('configuration:', 'simulated sensor:')) and any(
            word in lower for word in ('control','automation active','lane','drive started')
        ):
            category, color = 'CONTROL', '#60dfca'
        rows.append((f'{elapsed:06.1f}s  ·  {category}', color, index, True))
        line = ''
        for word in message.split():
            candidate = (line+' '+word).strip()
            if line and font.size(candidate)[0] > 279:
                rows.append((line, '#ecf3fa', index, False))
                line = word
            else:
                line = candidate
        rows.append((line, '#ecf3fa', index, False))
        rows.append(('', color, index, False))
    return rows


def draw_log(canvas, history, font, scroll):
    rows = log_rows(history, font)
    capacity = 20
    scroll = min(scroll, max(0, len(rows)-capacity))
    end = len(rows)-scroll
    start = max(0, end-capacity)
    latest = len(history)-1
    if scroll == 0:
        while start < end and not rows[start][3] and rows[start][2] != latest:
            start += 1
    previous_clip = canvas.get_clip()
    panel = pygame.Rect(1108,149,304,550)
    canvas.fill('#0e1720', panel)
    canvas.set_clip(panel)
    for i, (line,color,index,header) in enumerate(rows[start:end]):
        y = panel.y + i*27 + 5
        if index == latest and line:
            canvas.fill('#203543', (panel.left+4,y-3,panel.width-8,27))
        if header:
            pygame.draw.rect(canvas,color,(panel.left+5,y+3,2,16))
        canvas.blit(font.render(line,True,color),(panel.left+12,y))
    canvas.set_clip(previous_clip)
    status = 'Live · latest events' if scroll == 0 else 'History · End returns to live'
    canvas.blit(font.render(status,True,'#60dfca'),(1110,710))
    canvas.blit(font.render('Scroll · Page Up / Page Down',True,'#a7b8c9'),(1110,738))
    return scroll

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
    for index in range(9):
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
    """Windshield haze is strongest at the horizon and fades in the foreground."""
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
    for spacing, fall_speed, tilt, length, opacity, weight in (
        (154, 320, 4, 13, 78, 1),
        (81, 650, 10, 32, 138, 2),
    ):
        for index in range(round(spacing*intensity)):
            x = (index*97.53 + elapsed*76) % (width+tilt)
            y = (index*52.27 + elapsed*fall_speed) % (height+length) - length
            pygame.draw.line(rain,(211,232,243,opacity),(x,y),(x-tilt,y+length),weight)
    # A few beads near the edges suggest a wet windshield without hiding the road.
    for index in range(round(26*intensity)):
        x = 16 + (index*41.7) % 172
        if index % 2:
            x = width-x
        y = (index*29.2 + elapsed*(9+index%4)) % (height-30)
        radius = 1+index%3
        pygame.draw.circle(rain,(202,224,233,85),(x,y),radius,1)
    canvas.blit(rain,viewport.topleft)


def draw_windshield_trim(canvas, viewport):
    left, top, right, bottom = viewport.left, viewport.top, viewport.right, viewport.bottom
    for x, direction in ((left,1),(right,-1)):
        pygame.draw.polygon(canvas,'#141c24',[(x,top),(x+direction*18,top),
                                               (x+direction*30,bottom),(x,bottom)])
        pygame.draw.line(canvas,'#50616d',(x+direction*18,top),(x+direction*29,bottom),1)
    lip = [(left,bottom-18),(left+126,bottom-9),(right-126,bottom-9),
           (right,bottom-18),(right,bottom),(left,bottom)]
    pygame.draw.polygon(canvas,'#111820',lip)
    pygame.draw.lines(canvas,'#687780',False,lip[:4],1)


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
        canvas.fill('#202730', viewport)
        pygame.draw.polygon(canvas, '#343e48', [(viewport.left, horizon-58), (viewport.right, horizon-58),
                                                 viewport.bottomright, viewport.bottomleft])
        exit_depth = 37/(37+car.tunnel_length+gap)
        x, y = project(.5, exit_depth)
        pygame.draw.polygon(canvas, '#a2bcc3', arch(x, y, 10+exit_depth*265, 34+exit_depth*450))
    else:
        canvas.blit(sky(viewport.size,round(rain_intensity*20)),viewport.topleft)
        for index, color in enumerate(('#526675', '#3d555d')):
            hills = [(viewport.left, horizon+30)]
            for step in range(17):
                x = viewport.left + step*viewport.width/16
                height = math.sin(step*.93+index) * (19-index*5)
                hills.append((x, horizon-(32-index*20)+height))
            hills.append((viewport.right, horizon+30))
            pygame.draw.polygon(canvas, color, hills)
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
        for index in range(12):
            depth = ((index/12 + car.distance/91) % 1)**2
            lateral = -.4+(index*0.427) % 1.52
            color = road_color.lerp(pygame.Color('#627988'), rain_intensity*depth*.32)
            band(lateral,lateral+.35,color,depth,min(1,depth+.10))
    band(-.49,-.465,'#dbe2db')
    band(1.465,1.49,'#dbe2db')
    for index in range(13):
        offset = (index/13 + car.distance/105) % 1
        band(.489,.511,'#e0e6e1',offset**2,min(1,offset+.032)**2)

    for index in range(10):
        depth = ((index/10 + car.distance/135) % 1)**2
        for side in (-.77, 1.77):
            x, y = project(side, depth)
            if inside:
                lamp_y = y-15-160*depth
                pygame.draw.line(canvas, '#685f50', (x-14*depth,lamp_y), (x+14*depth,lamp_y), 4+round(5*depth))
                pygame.draw.line(canvas, '#e0c998', (x-8*depth,lamp_y), (x+8*depth,lamp_y), 2+round(2*depth))
            else:
                tip = y-3-27*depth
                pygame.draw.line(canvas, '#aab8b3', (x,y), (x,tip), max(1,round(4*depth)))
                if depth > .12:
                    pygame.draw.circle(canvas,'#dae1d9',(x,tip+2),max(1,round(3*depth)))

    if car.scenario == 'obstacle' and car.event_started and car.gap > -5:
        depth = 40/(max(0, car.gap)+40)
        x, y = project(car.config['obstacle_lane'], depth)
        width = 20 + depth*118
        bumper = pygame.Rect(x-width/2,y-width*.62,width,width*.62)
        pygame.draw.rect(canvas, '#101a21', bumper.inflate(7,5), border_radius=6)
        pygame.draw.rect(canvas, '#a7504b', bumper, border_radius=5)
        pygame.draw.line(canvas,'#d48678',bumper.topleft,bumper.topright,max(1,int(width*.035)))
        pygame.draw.rect(canvas, '#91adbe', (x-width*.31,y-width*.53,width*.62,width*.19), border_radius=2)
        pygame.draw.rect(canvas, '#464c50', (x-width*.15,y-width*.17,width*.30,width*.08), border_radius=2)
        for side in (-1, 1):
            pygame.draw.circle(canvas, '#ffab63', (x+side*width*.36,y-width*.13), max(2,int(width*.06)))
        size = max(7,width*.16)
        triangle_x = x + width*.65
        pygame.draw.polygon(canvas, '#ffbc70', [(triangle_x,y-size*1.5),(triangle_x-size,y),(triangle_x+size,y)], 2)
    if storm:
        draw_rain(canvas,viewport,rain_intensity,car.elapsed)
    draw_windshield_trim(canvas,viewport)
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

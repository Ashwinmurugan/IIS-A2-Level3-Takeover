"""Road illustration and observer log. All inputs come from the simulator."""
from functools import lru_cache
import math

import pygame


@lru_cache(maxsize=24)
def sky(size, storm_level):
    surface = pygame.Surface(size)
    storm = storm_level / 20
    top = pygame.Color('#527f9b').lerp(pygame.Color('#303e4d'), storm)
    base = pygame.Color('#dce5de').lerp(pygame.Color('#9dabb1'), storm)
    for y in range(size[1]):
        color = top.lerp(base, min(1, y / max(1, size[1]*.43)))
        pygame.draw.line(surface, color, (0, y), (size[0], y))
    # Several translucent lobes softened at low resolution avoid flat oval clouds.
    low = pygame.Surface((max(1,size[0]//4), max(1,size[1]//4)), pygame.SRCALPHA)
    tint = pygame.Color(245,247,239,68).lerp(pygame.Color(55,66,77,59), storm)
    for index in range(12):
        x = (index//4)*low.get_width()*.42 + (index%4)*8-18
        y = 3 + (index//4)*4 + (index%3)*2
        width = 23 + (index*11) % 17
        pygame.draw.ellipse(low, tint, (x,y,width,5+(index%3)))
    soft = pygame.transform.smoothscale(low,(max(1,size[0]//14),max(1,size[1]//14)))
    surface.blit(pygame.transform.smoothscale(soft,size),(0,0))
    # Haze and distant ridgelines are part of the cached background.
    for level, color in enumerate(('#8fa6aa','#728d90','#587575')):
        points = [(0,109)]
        for step in range(101):
            x = step*size[0]/100
            ridge = 69+level*11 - 9*math.sin(step*.097+level*2) - 5*math.sin(step*.31)
            points.append((x,ridge))
        points.append((size[0],109))
        pygame.draw.polygon(surface, pygame.Color(color).lerp(pygame.Color('#76888e'),storm*.55), points)
    return surface


@lru_cache(maxsize=256)
def tree_sprite(height, variant, storm_level):
    """Small cached roadside silhouettes; no assets or random frame flicker."""
    height = max(8,height)
    width = max(8,round(height*.66))
    layer = pygame.Surface((width*2,height*2), pygame.SRCALPHA)
    cx, bottom = width, height*2-2
    storm = storm_level/20
    trunk = pygame.Color('#5e6554').lerp(pygame.Color('#3b4d4d'),storm)
    dark = pygame.Color('#304b42').lerp(pygame.Color('#344c4f'),storm)
    mid = pygame.Color('#456452').lerp(pygame.Color('#415b5c'),storm)
    pygame.draw.line(layer,trunk,(cx,bottom),(cx,height*.7),max(2,round(height*.10)))
    for branch in range(8):
        angle = branch*2.39+variant
        rx = cx+math.cos(angle)*width*.35
        ry = height*.85+math.sin(angle)*height*.32
        radius = max(3,round(height*(.31+(branch%3)*.025)))
        pygame.draw.circle(layer,dark if branch%3 else mid,(rx,ry),radius)
    return pygame.transform.smoothscale(layer,(width,height))


def lamp(canvas, x, y, radius, warmth):
    """Restrained light bloom, rendered only within the road viewport."""
    radius = max(3,round(radius))
    glow = pygame.Surface((radius*4,radius*4),pygame.SRCALPHA)
    for scale, alpha in ((2,10),(1.5,17),(1,35),(.55,80)):
        pygame.draw.ellipse(glow,(*warmth,alpha),
                            (radius*(2-scale),radius*(2-scale)*.8+radius*.4,
                             radius*scale*2,radius*scale*1.6))
    canvas.blit(glow,(x-radius*2,y-radius*2))


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
        canvas.fill('#141c24', viewport)
        for side, color in ((-1,'#2b353d'),(1,'#222c35')):
            wall = viewport.left if side < 0 else viewport.right
            pygame.draw.polygon(canvas,color,[(wall,viewport.top),(vanishing_x,horizon-34),
                                               (vanishing_x,horizon+8),(wall,ground)])
        for index in range(12):
            depth = ((index/12 + car.distance/135) % 1)**2
            x, y = project(.5,depth)
            pygame.draw.lines(canvas,'#35434d',False,arch(x,y,19+depth*344,22+depth*330),max(1,round(2*depth)))
        # Continuous services and wall panels converge with the road.
        for side in (-.72,1.72):
            for rise, color in ((36,'#48565e'),(48,'#384751'),(90,'#25343f')):
                points=[]
                for depth in (0,.2,.5,1):
                    x,y=project(side,depth)
                    points.append((x,y-rise*depth))
                pygame.draw.lines(canvas,color,False,points,2)
        exit_depth = 37/(37+car.tunnel_length+gap)
        x, y = project(.5, exit_depth)
        width, height = 10+exit_depth*265, 22+exit_depth*330
        pygame.draw.polygon(canvas,'#738f9b',arch(x,y,width+5,height+5))
        pygame.draw.polygon(canvas,'#c2d8dd',arch(x,y,width,height))
    else:
        canvas.blit(sky(viewport.size,round(rain_intensity*20)),viewport.topleft)
        near = pygame.Color('#405946').lerp(pygame.Color('#3f5554'),rain_intensity)
        far = pygame.Color('#738875').lerp(pygame.Color('#687d7d'),rain_intensity)
        for row in range(ground-horizon):
            depth = row/(ground-horizon)
            color = far.lerp(near,min(1,depth*1.6))
            pygame.draw.line(canvas,color,(viewport.left,horizon+row),(viewport.right,horizon+row))
        # Sparse verge texture travels with the ground, not with elapsed wall time.
        for index in range(70):
            depth=((index/70+car.distance/190)%1)**2
            side=-1.1-(index*.37)%4.2 if index%2 else 2.1+(index*.41)%4.2
            x,y=project(side,depth)
            pygame.draw.line(canvas,'#4b6451',(x,y),(x+7*depth,y-2*depth),max(1,round(depth*2)))
        for index in reversed(range(18)):
            ahead=(index*23-car.distance)%414
            depth=32/(32+ahead)
            for side in (-1,1):
                lateral=-2.15 if side<0 else 3.15
                x,y=project(lateral+((index*1.37)%2.6)*side,depth)
                height=round(10+depth*(110+(index%3)*20))
                tree=tree_sprite(height,index%3,round(rain_intensity*20))
                if viewport.left-tree.get_width()<x<viewport.right+tree.get_width():
                    pygame.draw.ellipse(canvas,'#344e42',(x-tree.get_width()*.3,y-3,tree.get_width()*.9,max(2,height*.08)))
                    canvas.blit(tree,(x-tree.get_width()/2,y-height))
        if tunnel and gap > 0:
            depth = 43/(43+gap)
            x, bottom = project(.5, depth)
            width = 11+depth*300
            height = 20+depth*390
            pygame.draw.polygon(canvas, '#92a1a6', arch(x,bottom,width,height))
            pygame.draw.polygon(canvas, '#53636b', arch(x,bottom,width*.88,height*.91))
            pygame.draw.polygon(canvas, '#1a2129', arch(x,bottom,width*.75,height*.80))
            pygame.draw.lines(canvas,'#bdc5c1',False,arch(x,bottom,width*.94,height*.96),max(1,round(depth*4)))
            for side in (-1,1):
                lamp_x=x+side*width*.56
                lamp_y=bottom-height*.57
                lamp(canvas,lamp_x,lamp_y,2+depth*3,(249,221,169))
                pygame.draw.line(canvas,'#ffe1a7',(lamp_x-2-depth*3,lamp_y),(lamp_x+2+depth*3,lamp_y),max(1,round(depth*3)))

    band(-.67,1.67,'#596671' if inside else '#747b76')
    road_color = pygame.Color('#353f49').lerp(pygame.Color('#283641'), rain_intensity)
    band(-.5,1.5,road_color)
    # Fine depth shading adds asphalt volume without noisy animated texture.
    for strip in range(40):
        depth = strip/40
        shade = road_color.lerp(pygame.Color('#17212b'), depth*.18)
        band(-.5,1.5,shade,depth,(strip+1)/40)
    for index in range(150):
        depth=((index/150+car.distance/105)%1)**2
        lateral=-.46+(index*.617)%1.92
        x,y=project(lateral,depth)
        color=road_color.lerp(pygame.Color('#bac1c1'),.035+depth*.025)
        pygame.draw.line(canvas,color,(x,y),(x+max(1,depth*2),y),1)
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
                lamp(canvas,x,lamp_y,2+depth*7,(246,218,165))
                pygame.draw.line(canvas, '#685f50', (x-14*depth,lamp_y), (x+14*depth,lamp_y), 4+round(5*depth))
                pygame.draw.line(canvas, '#f7deaa', (x-9*depth,lamp_y), (x+9*depth,lamp_y), 2+round(2*depth))
            else:
                tip = y-3-27*depth
                pygame.draw.line(canvas, '#293e38', (x,y), (x+23*depth,y+5*depth),
                                 max(1,round(3*depth)))
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
        pygame.draw.line(canvas, '#633b3e', (x-width*.43,y-width*.27),
                         (x+width*.43,y-width*.27), max(1,round(width*.025)))
        pygame.draw.line(canvas, '#c6cdd0', (x-width*.42,y-width*.04),
                         (x+width*.42,y-width*.04), max(1,round(width*.025)))
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

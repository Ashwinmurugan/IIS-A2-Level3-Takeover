"""Distance-driven road view and readable observer log."""
import pygame


def draw_road(canvas, car):
    viewport = pygame.Rect(354, 238, 688, 252)
    canvas.set_clip(viewport)
    remaining = car.boundary - car.distance
    inside = car.scenario == 'tunnel' and 0 <= car.distance-car.boundary < car.tunnel_length
    canvas.fill('#202630' if inside else '#718896', viewport)
    centre = 698 + (.5-car.position)*300
    pygame.draw.polygon(canvas, '#344e45' if not inside else '#292e36', [(354,280),(1042,280),(1042,490),(354,490)])
    if car.scenario == 'tunnel' and remaining > 0:
        scale = 75/(remaining+75)
        width = 35 + 800*scale
        bottom = 280 + 230*scale
        portal = pygame.Rect(698-width, bottom-width*1.2, width*2, width*1.2)
        pygame.draw.rect(canvas, '#93999b', portal, border_radius=max(1,int(width*.45)))
        inner = portal.inflate(-max(8,width*.15), -max(8,width*.15))
        pygame.draw.rect(canvas, '#171e26', inner, border_radius=max(1,int(width*.4)))
    pygame.draw.polygon(canvas, '#333b46', [(678,280),(718,280),(centre+300,490),(centre-300,490)])
    for i in range(14):
        depth = ((i/14 + car.distance/100) % 1)**2
        y = 280+depth*210
        x = 698+(centre-698)*depth
        pygame.draw.line(canvas, '#f0ede0', (x,y), (x,y+4+depth*13), max(1,int(depth*5)))
    if inside:
        for i in range(8):
            depth = ((i/8+car.distance/120)%1)**2
            half_width = 30+depth*500
            y = 275+depth*200
            pygame.draw.line(canvas, '#9c9b80', (698-half_width,y-70-depth*160), (698-half_width,y), 3)
            pygame.draw.line(canvas, '#9c9b80', (698+half_width,y-70-depth*160), (698+half_width,y), 3)
        to_exit = car.boundary+car.tunnel_length-car.distance
        width = 20+500*60/(to_exit+60)
        pygame.draw.rect(canvas, '#c4dbe5', (698-width,245,width*2,35))
    if car.scenario == 'obstacle' and car.event_started and car.gap > -5:
        depth = 40/(max(0,car.gap)+40)
        x = 698+(car.config['obstacle_lane']-car.position)*300*depth
        y = 280+depth*210
        width = 20+depth*110
        pygame.draw.rect(canvas,'#aa3b42',(x-width/2,y-width*.6,width,width*.6),border_radius=5)
        pygame.draw.rect(canvas,'#91b3c3',(x-width*.32,y-width*.55,width*.64,width*.2))
        for side in (-1,1):
            pygame.draw.circle(canvas,'#ffb04f',(int(x+side*width*.35),int(y-width*.14)),max(2,int(width*.055)))
    if car.scenario == 'rain' and car.rain_intensity > 0:
        fog = pygame.Surface(viewport.size,pygame.SRCALPHA)
        fog.fill((130,150,170,int(car.rain_intensity*110)))
        canvas.blit(fog,viewport.topleft)
        for i in range(int(140*car.rain_intensity)):
            x = 354+(i*73+car.elapsed*70)%688
            y = 238+(i*47+car.elapsed*420)%252
            pygame.draw.line(canvas,'#b8d5e6',(x,y),(x-8,y+20),2)
    canvas.set_clip(None)


def log_rows(history, font):
    rows = []
    for elapsed, message in history:
        lower = message.lower()
        category, color = 'OBSERVATION', '#d4e1ec'
        if any(word in lower for word in ('warning','unavailable','deadline','attention','hazard','rejected','takeover requested','collision','emergency')):
            category, color = 'ALERT', '#ffc369'
        elif any(word in lower for word in ('control','automation active','lane','drive started')):
            category, color = 'CONTROL', '#51dbc4'
        rows.append((f'{elapsed:06.1f}s  {category}', color))
        line = ''
        for word in message.split():
            candidate = (line+' '+word).strip()
            if line and font.size(candidate)[0] > 302:
                rows.append((line, '#eef4fa'))
                line = word
            else:
                line = candidate
        rows.append((line, '#eef4fa'))
        rows.append(('', color))
    return rows


def draw_log(canvas, history, font, scroll):
    rows = log_rows(history, font)
    count = 18
    scroll = min(scroll, max(0,len(rows)-count))
    end = len(rows)-scroll
    canvas.set_clip(pygame.Rect(1088,165,326,540))
    for i,(line,color) in enumerate(rows[max(0,end-count):end]):
        canvas.blit(font.render(line,True,color),(1092,165+i*29))
    canvas.set_clip(None)
    label = 'LIVE - latest events' if scroll == 0 else 'History - END returns to live'
    canvas.blit(pygame.font.SysFont('Segoe UI',18).render(label,True,'#51dbc4'),(1092,719))
    canvas.blit(pygame.font.SysFont('Segoe UI',18).render('Scroll wheel / PgUp / PgDn',True,'#d4e1ec'),(1092,745))
    return scroll

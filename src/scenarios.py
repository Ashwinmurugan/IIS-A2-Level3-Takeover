"""Validated configuration for reproducible simulation scenarios."""
import json
import math
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'scenarios.json'


def load_settings(path=DEFAULT_PATH):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    required = {
        'tunnel': ('start_speed','start_lane','event_at','tunnel_length'),
        'obstacle': ('start_speed','start_lane','event_at','obstacle_at','obstacle_lane','detection_range'),
        'rain': ('start_speed','start_lane','event_at','rain_duration','rain_peak','visibility_limit','recovery_seconds'),
        'rules': ('request_seconds','urgent_seconds','fallback_seconds','deceleration','emergency_deceleration','stop_margin','attention_seconds','rain_speed')}
    for name, fields in required.items():
        for field in fields:
            value = data[name][field]
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'{name}.{field} must be finite and nonnegative')
    for name in ('tunnel','obstacle','rain'):
        if not 0 < data[name]['start_speed'] <= 100 or data[name]['start_lane'] not in (0,1):
            raise ValueError('Starting speed must be 1–100 and lane 0 or 1')
    r, o, rain = data['rules'], data['obstacle'], data['rain']
    if not r['request_seconds'] > r['urgent_seconds'] > r['fallback_seconds'] > 0:
        raise ValueError('Warning times must be descending and positive')
    if not r['emergency_deceleration'] >= r['deceleration'] > 0:
        raise ValueError('Decelerations must be positive and ordered')
    if o['obstacle_lane'] not in (0,1) or o['obstacle_at'] <= o['event_at'] or o['detection_range'] <= 0:
        raise ValueError('Obstacle must appear ahead in a valid lane with positive sensing range')
    if not 0 < rain['rain_peak'] <= 1 or rain['rain_duration'] < 10 or not 0 < rain['visibility_limit'] < 220 or rain['recovery_seconds'] <= 0:
        raise ValueError('Invalid rain settings')
    if data['tunnel']['tunnel_length'] <= 0 or r['attention_seconds'] <= 0 or r['rain_speed'] <= 0:
        raise ValueError('Lengths, attention time and rain speed must be positive')
    return data

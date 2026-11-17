"""Experimental orientation and eye-closure cues, not a readiness assessment."""
import math


def pose_from_rotation(rotation):
    yaw = math.degrees(math.atan2(rotation[0, 2], rotation[2, 2]))
    pitch = math.degrees(math.atan2(-rotation[1, 2], math.hypot(rotation[0, 2], rotation[2, 2])))
    return yaw, pitch


def valid_camera_sample(sample, now):
    frame, observation, stamp, status = sample
    if now-stamp >= .75:
        return None, None, stamp, 'Tracking unavailable - no fresh camera data'
    if observation is not None and not all(math.isfinite(v) for v in observation[:2]):
        return frame, None, stamp, 'Tracking unavailable - invalid estimate'
    return frame, observation, stamp, status


class Monitor:
    def __init__(self):
        self.closed_since = None

    def classify(self, observation, baseline, now):
        if observation is None or baseline is None:
            self.closed_since = None
            return ('Unavailable' if observation is None else 'Needs calibration'), 'Unknown', None
        yaw, pitch, blink = observation
        yaw = (yaw - baseline[0] + 180) % 360 - 180
        pitch = (pitch - baseline[1] + 180) % 360 - 180
        if abs(pitch) > 18 and abs(pitch)/18 > abs(yaw)/25:
            head = 'Looking up' if pitch < 0 else 'Looking down'
        elif abs(yaw) > 25:
            head = 'Looking left' if yaw > 0 else 'Looking right'
        else:
            head = 'Facing forward'
        if not math.isfinite(blink):
            self.closed_since = None
            eyes = 'Unknown'
        elif blink >= .65:
            if self.closed_since is None:
                self.closed_since = now
            eyes = 'Eyes appear closed' if now-self.closed_since >= 1.5 else 'Brief closure'
        else:
            self.closed_since = None
            eyes = 'Open estimate'
        return head, eyes, (yaw, pitch)


def verify():
    monitor = Monitor()
    assert monitor.classify((0, 0, .9), (0, 0), 0)[1] == 'Brief closure'
    assert monitor.classify((0, 0, .9), (0, 0), 1.6)[1] == 'Eyes appear closed'
    assert monitor.classify(None, (0, 0), 2)[1] == 'Unknown'
    assert monitor.classify((0, 0, .9), (0, 0), 2.1)[1] == 'Brief closure'
    assert monitor.classify((0, -30, 0), (0, 0), 3)[0] == 'Looking up'
    assert monitor.classify((0, 30, 0), (0, 0), 3)[0] == 'Looking down'
    assert monitor.classify((40, 0, 0), (0, 0), 3)[0] == 'Looking left'
    assert monitor.classify((-40, 0, 0), (0, 0), 3)[0] == 'Looking right'
    print('PASS: orientation, blink duration, sustained closure and tracking-loss reset')


if __name__ == '__main__':
    verify()

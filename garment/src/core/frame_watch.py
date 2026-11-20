# 역할: Blender 외부에서 프레임별 계산 제한시간을 감시합니다.
import math


def limit(value, default):
    try: value=float(value)
    except (TypeError,ValueError): return default
    return value if math.isfinite(value) and .05 <= value <= 180 else default


class FrameWatch:
    def __init__(self, first=60., subsequent=30.):
        self.first=first; self.subsequent=subsequent
        self.frame=None; self.started=None

    def observe(self, event, now):
        frame=event.get('frame')
        if type(frame) is not int or frame < 1: return
        if event.get('stage') == 'cloth_frame_start':
            if self.frame != frame:
                self.frame=frame; self.started=now
        elif event.get('stage') in ('cloth_frame','cloth_frame_complete') and self.frame == frame:
            self.frame=None; self.started=None

    def expired(self, now):
        if self.frame is None: return None
        timeout=self.first if self.frame == 1 else self.subsequent
        elapsed=now-self.started
        if elapsed < timeout: return None
        return {'frame':self.frame,'frame_elapsed_seconds':elapsed,'frame_limit_seconds':timeout}

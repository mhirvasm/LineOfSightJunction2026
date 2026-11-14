"""Stable head-directed selection with short freshness limits."""


class TargetTracker:
    def __init__(self, acquire_seconds=.35, expire_seconds=.6):
        self.acquire_seconds = acquire_seconds
        self.expire_seconds = expire_seconds
        self.clear()

    def clear(self):
        self.candidate_id = None
        self.since = None
        self.locked_id = None
        self.last_seen = None

    def expire(self, now):
        if self.last_seen is not None and now - self.last_seen >= self.expire_seconds:
            self.clear()
            return True
        return False

    def observe(self, candidate_id, now, unsafe=False):
        self.expire(now)
        if unsafe:
            self.clear()
            return
        if candidate_id is None:
            self.candidate_id = None
            self.since = None
            return
        if candidate_id != self.candidate_id:
            self.candidate_id = candidate_id
            self.since = now
            if self.locked_id != candidate_id:
                self.locked_id = None
        self.last_seen = now
        if now - self.since >= self.acquire_seconds:
            self.locked_id = candidate_id

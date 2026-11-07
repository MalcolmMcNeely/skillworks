from datetime import datetime, timedelta, timezone

HELD_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)


class HeldClock:
    def __init__(self):
        self.at = HELD_AT
        self.repeats = []

    def now(self):
        return self.at

    def every(self, seconds, do):
        repeat = {"due": self.at + timedelta(seconds=seconds), "every": timedelta(seconds=seconds),
                  "do": do}
        self.repeats.append(repeat)
        return lambda: self.repeats.remove(repeat) if repeat in self.repeats else None

    # Each repeat runs at the moment it falls due, so a long move reads as the beats it spans.
    def move(self, seconds):
        until = self.at + timedelta(seconds=seconds)
        while True:
            due = [repeat for repeat in self.repeats if repeat["due"] <= until]
            if not due:
                break
            repeat = min(due, key=lambda each: each["due"])
            self.at = repeat["due"]
            repeat["due"] += repeat["every"]
            repeat["do"]()
        self.at = until

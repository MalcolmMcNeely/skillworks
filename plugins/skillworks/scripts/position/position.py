# The driver writes it and the pane reads it, so these fields are the contract between the two.

import json
from datetime import timedelta
from pathlib import Path

POSITION = "position.json"

BASELINE = "baseline"
CUTTING = "cutting"
BUILDING = "building tickets"
FULL_RUN = "full run"
DEEPENING_CHECK = "Deepening check"
SIMPLIFY_CHECK = "Simplify check"
DRIFT_CHECK = "drift check"
NAME_CHECK = "Name check"
FINISHED = "finished"
STOPPED = "stopped"

TO_COME = "to come"
NOW = "now"
DONE = "done"
OFF = "off"

# Read by the pane in a language of its own, so the form is one any date parser takes.
TIME_FORM = "%Y-%m-%dT%H:%M:%SZ"

# Often enough that a pane reading a heartbeat older than two minutes as gone never misreads a live loop.
HEARTBEAT_SECONDS = 30


def position_time(moment):
    return moment.strftime(TIME_FORM)


class Position:
    def __init__(self, judges):
        self.judges = judges
        self.doing = None
        self.judged = {judge.name: {"name": judge.name, "state": TO_COME, "found": None,
                                    "word": judge.word} for judge in judges}
        self.tickets = []
        self.ticket_now = None

    @property
    def ticket_count(self):
        return len(self.tickets)

    def tickets_read(self, rows):
        self.tickets = [{"number": number, "title": title, "landed": state == "closed",
                         "judge": self.filed_by(title)} for number, state, title in rows]

    def filed_by(self, title):
        return next((judge.name for judge in self.judges if judge.filed(title)), None)

    def filed(self, ticket, title, judge):
        self.tickets.append({"number": ticket, "title": title, "landed": False, "judge": judge.name})

    def judge_is(self, judge, state):
        self.judged[judge.name]["state"] = state

    def judge_found(self, judge, count):
        self.judged[judge.name]["found"] = count

    def started(self, ticket, title, steps):
        self.ticket_now = {"number": ticket, "title": title, "steps": steps,
                           "step": None, "step_started": None}

    def on_step(self, name, now):
        if self.ticket_now is not None:
            self.ticket_now["step"] = name
            self.ticket_now["step_started"] = position_time(now)

    def landed(self, ticket):
        for row in self.tickets:
            if row["number"] == ticket:
                row["landed"] = True
        self.ticket_now = None

    def to_write(self, spec, run, now, at, seconds_left, choices, denials, stop):
        return {
            "spec": spec,
            "run": run,
            "heartbeat": position_time(now),
            "doing": self.doing,
            "judges": [{**judged, "filed": [row["number"] for row in self.tickets if row["judge"] == name]}
                       for name, judged in self.judged.items()],
            "tickets": self.tickets,
            "ticket": self.ticket_now,
            "at": at or None,
            "of": self.ticket_count or None,
            "seconds_left": seconds_left,
            "choices": choices,
            "denials": denials,
            "stop": stop,
        }


# Short, because the write holds the lock both writers share, so a step change waits this long at most.
PATIENCE = timedelta(seconds=1)
# Long, because the heartbeat stops before the end write and nothing writes the Position after it.
END_PATIENCE = timedelta(seconds=30)
TRY_EVERY_SECONDS = 0.05


# Renamed into place, so a reader that opens the file between two writes never reads half of one.
# A failure is handed back and never raised, because a display file must not end a heartbeat or a run.
def written_whole(path, position, replace, clock, patience=PATIENCE):
    path = Path(path)
    beside = path.with_name(path.name + ".tmp")
    try:
        beside.write_text(json.dumps(position, indent=2) + "\n", encoding="utf-8", newline="\n")
    except OSError as failed:
        return failed
    began = clock.now()
    while True:
        try:
            replace(beside, path)
            return None
        # Windows refuses a replace while the pane reads the file, and that clears by itself.
        except PermissionError as held:
            if clock.now() - began >= patience:
                return held
            clock.wait(TRY_EVERY_SECONDS)
        except OSError as failed:
            return failed

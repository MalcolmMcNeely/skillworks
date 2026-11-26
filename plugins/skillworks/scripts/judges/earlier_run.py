# A judge runs once for each spec, so a rerun takes what an earlier run left on the Tracker in place of running it.

from typing import NamedTuple


class EarlierRun(NamedTuple):
    report: str
    tickets: list

    @property
    def ticket(self):
        return self.tickets[0][0] if self.tickets else None


# Tickets are found by the title their template writes, since the Tracker keeps no other mark of who filed one.
def earlier_run(tracker, spec, judge):
    return EarlierRun(judge.earlier(tracker, spec) or "",
                      [(number, title) for number, _, title in tracker.ticket_rows(spec)
                       if judge.filed(title)])

# All of a judge comes from its step name, so its skill, Sessions, report file and log files cannot drift apart.

from typing import Callable, NamedTuple

from count.deepening_ticket import TITLE as DEEPENING_TITLE
from count.gap_ticket import TITLE as GAP_TITLE
from count.rename_ticket import TITLE as RENAME_TITLE
from count.simplify_ticket import TITLE as SIMPLIFY_TITLE
from position.position import DEEPENING_CHECK, DRIFT_CHECK, NAME_CHECK, SIMPLIFY_CHECK


class Judge(NamedTuple):
    name: str
    what: str
    tag: str
    report: str
    read: Callable
    earlier: Callable
    filed: Callable
    lost: str
    lost_again: str = ""

    @property
    def skill(self):
        return "spec-" + self.name

    @property
    def report_file(self):
        return self.name.replace("-check", "-report") + ".md"

    @property
    def rechecks(self):
        return bool(self.lost_again)

    def session(self, again=False):
        return self.name.replace("-check", "-re-check") if again else self.name

    def said_as(self, again=False):
        return self.what.replace("check", "re-check") if again else self.what

    def log_file(self, again=False):
        return self.session(again) + ".md"


DEEPENING = Judge(
    "deepening-check", DEEPENING_CHECK, "DEEPEN", "Deepening report",
    read=lambda tracker, spec: tracker.deepening_report(spec),
    earlier=lambda tracker, spec: tracker.deepening_report(spec),
    filed=lambda title: title.startswith(DEEPENING_TITLE),
    lost="no deepening was read")
SIMPLIFY = Judge(
    "simplify-check", SIMPLIFY_CHECK, "SIMPLIFY", "Simplify report",
    read=lambda tracker, spec: tracker.simplify_report(spec),
    earlier=lambda tracker, spec: tracker.simplify_report(spec),
    filed=lambda title: title == SIMPLIFY_TITLE,
    lost="no cleanup was read")
DRIFT = Judge(
    "drift-check", DRIFT_CHECK, "DRIFT", "drift report",
    read=lambda tracker, spec: tracker.drift_report(spec),
    earlier=lambda tracker, spec: tracker.earlier_drift_report(spec),
    filed=lambda title: title == GAP_TITLE,
    lost="nothing was counted", lost_again="the Gap items were not judged again")
NAMES = Judge(
    "name-check", NAME_CHECK, "NAMES", "Name report",
    read=lambda tracker, spec: tracker.name_report(spec),
    earlier=lambda tracker, spec: tracker.earlier_name_report(spec),
    filed=lambda title: title == RENAME_TITLE,
    lost="no name was read", lost_again="no rename was checked")

# In the order the loop runs them.
JUDGES = (DEEPENING, SIMPLIFY, DRIFT, NAMES)


def told_to_judge():
    return [session for judge in JUDGES
            for session in ([judge.session(), judge.session(again=True)] if judge.rechecks
                            else [judge.session()])]

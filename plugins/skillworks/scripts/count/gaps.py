# Pure, so each kind of Gap is proved on the spec's text and the report's, and never on a run.

from typing import NamedTuple

from count.verdicts import CONTRADICTS, MISSING, OUT_OF_STEP, PARTIAL

GAP_WORDS = (MISSING, PARTIAL, OUT_OF_STEP)


class Gap(NamedTuple):
    item: object
    # Every Verdict the report gave the item, so none, one and two are told apart by the length.
    judged: list


class Count(NamedTuple):
    gaps: list
    contradicts: list
    # A Verdict for an item the spec does not hold, most often a typo, so it counts for nothing.
    unknown: list
    verdicts_given: int


def gap_said(gap):
    name = gap.item.name
    if not gap.judged:
        return "{} has no Verdict".format(name)
    if len(gap.judged) > 1:
        return "{} has {} Verdicts: {}".format(
            name, len(gap.judged), ", ".join(verdict.word for verdict in gap.judged))
    said = "{} is {}".format(name, gap.judged[0].word)
    return said + ": " + gap.judged[0].reason if gap.judged[0].reason else said


def count_verdicts(items, verdicts):
    judged = {item.name: [] for item in items.every()}
    unknown = []
    for verdict in verdicts:
        if verdict.item in judged:
            judged[verdict.item].append(verdict)
        else:
            unknown.append(verdict)

    gaps = []
    for item in items.every():
        given = judged[item.name]
        if len(given) != 1 or given[0].word in GAP_WORDS:
            gaps.append(Gap(item, given))
    contradicts = [verdict for verdict in verdicts
                   if verdict.item in judged and verdict.word == CONTRADICTS]
    return Count(gaps, contradicts, unknown, len(verdicts))

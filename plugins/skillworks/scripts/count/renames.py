# Pure, so each way a Name report can write a rename is proved on a string and never on a run.

from typing import NamedTuple

from count.verdicts import NAME_MARKS, SEPARATOR, VERDICTS, bullets, subsections_of, verdict_in

RENAMES = "### Renames"

DONE = "Done"
NOT_DONE = "Not done"

RENAME_WORDS = (NOT_DONE, DONE)

# The words spec-names is told to write, so the driver can say which concept no glossary names.
NO_GLOSSARY_WORD = "no glossary word"


class Unmade(NamedTuple):
    name: str
    # Every Verdict the Name re-check gave the rename, so none, one and two are told apart by the length.
    judged: list


class RenameCount(NamedTuple):
    unmade: list
    # A Verdict for a rename the ticket does not owe, most often a typo, so it counts for nothing.
    unknown: list
    verdicts_given: int


# None when the report holds no Renames list, which is a different fault from an empty one.
def read_renames(report):
    held = subsections_of(report)
    if RENAMES not in held:
        return None
    return [said for said in bullets(held[RENAMES]) if said.rstrip(".") != "None"]


def name_of(said):
    return said.split(SEPARATOR, 1)[0].strip(NAME_MARKS)


def has_no_glossary_word(said):
    return NO_GLOSSARY_WORD in said.lower()


# None when the report holds no Verdicts list, which is a different fault from an empty one.
def read_rename_verdicts(report):
    held = subsections_of(report)
    if VERDICTS not in held:
        return None
    return [verdict for verdict in (verdict_in(said, RENAME_WORDS) for said in bullets(held[VERDICTS]))
            if verdict]


def unmade_said(unmade):
    if not unmade.judged:
        return "{} has no Verdict".format(unmade.name)
    if len(unmade.judged) > 1:
        return "{} has {} Verdicts: {}".format(
            unmade.name, len(unmade.judged), ", ".join(verdict.word for verdict in unmade.judged))
    said = "{} is {}".format(unmade.name, unmade.judged[0].word)
    return said + ": " + unmade.judged[0].reason if unmade.judged[0].reason else said


def count_renames(renames, verdicts):
    judged = {name_of(said): [] for said in renames}
    unknown = []
    for verdict in verdicts:
        if verdict.item in judged:
            judged[verdict.item].append(verdict)
        else:
            unknown.append(verdict)
    unmade = [Unmade(name, given) for name, given in judged.items()
              if len(given) != 1 or given[0].word != DONE]
    return RenameCount(unmade, unknown, len(verdicts))

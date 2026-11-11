from seeds import merge
from steering.steering_file import STEERING_FOLDER

BASES = STEERING_FOLDER + "/.seeds"

CHOOSE = "--keep <file>:<overlap>=yours|seed or --blend <file>:<overlap>=<blend file> for each overlap"

SETTLE = "--settled <file> for each file that differs from its seed"

ASKS = {merge.ASKS_OVERLAP: CHOOSE, merge.ASKS_SETTLE: SETTLE}


class Outcome:
    def __init__(self, done, would=None, shown=(), writes=(), asks=None, used=(), makes=(), does=()):
        self.done = done
        self.would = would or done
        self.shown = list(shown)
        self.writes = list(writes)
        self.makes = list(makes)
        self.does = list(does)
        self.asks = asks
        self.used = set(used)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


# A run that stops for a question writes nothing, so no Steering file is left half-merged while the team decides.
def report(outcomes, step, out):
    asking = [ask for ask in (CHOOSE, SETTLE) if any(outcome.asks == ask for outcome in outcomes)]
    for outcome in outcomes:
        out.write(outcome.would if asking else outcome.done)
        out.writelines(outcome.shown)
        if not asking:
            for do in outcome.does:
                do()
            for path, text in outcome.writes:
                write(path, text)
            for path in outcome.makes:
                path.mkdir(parents=True, exist_ok=True)
    if asking:
        out.write("Nothing was written. Run again with {}.\n".format(" and ".join(asking)))
    else:
        out.write(step)

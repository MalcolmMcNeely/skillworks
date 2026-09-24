#
# How a script stops, and what it says on the way out.
#
#   raise refusal("origin has no main branch. Nothing was pushed.")
#   raise misuse(USAGE)
#
# One module, because two scripts answering different numbers for the same event is a
# fault nothing goes red on. A refusal exits 1 and its reason goes to stderr behind
# FAIL. A command built wrong exits 64 and prints the usage.
#
# The caller decides what to do with a Stop. An entry point writes what it says and
# exits with its number.

REFUSED = 1
MISUSED = 64


class Stop(Exception):
    def __init__(self, status, said):
        super().__init__(said)
        self.status = status
        self.said = said


def refusal(said):
    return Stop(REFUSED, "FAIL  " + said + "\n")


def misuse(usage):
    return Stop(MISUSED, usage)


# `isdigit` answers yes to a superscript and an Arabic-Indic digit, so the letters are named.
def is_a_number(said):
    return bool(said) and all(c in "0123456789" for c in said)

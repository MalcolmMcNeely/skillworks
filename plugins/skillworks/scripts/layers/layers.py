from dataclasses import dataclass
from pathlib import Path

from runner import Subprocess
from sidecar.locator import sidecar_of
from stop import Stop

# Every script builds its Steering paths from this one name, so the folder moves in one line.
STEERING_FOLDER = "docs/skillworks"

LOOP_FILE = STEERING_FOLDER + "/loop.json"

REPO = "repo"

SIDECAR = "Sidecar"


# The label is a field and not text, so another Layer, such as remote Steering, adds a value and no new format.
@dataclass(frozen=True)
class Layer:
    root: Path
    prefix: str
    label: str


@dataclass(frozen=True)
class RepoSteering:
    repo: Layer
    sidecar: Layer | None

    # Under Sidecar Steering the Sidecar holds the Steering files, and the repo holds none of them.
    @property
    def steering(self):
        return self.sidecar or self.repo

    def layers(self):
        return [self.repo] + ([self.sidecar] if self.sidecar else [])

    # Neither copy may win, because the one that won would hide the newer edits in the other.
    def loop_file_in_both(self):
        repo_copy = self.repo.root / LOOP_FILE
        if self.sidecar is None or not repo_copy.is_file():
            return None
        return ("both the repo and the Sidecar hold {}, so neither may win: {} and {}. Remove one of the two.".format(
            LOOP_FILE, repo_copy.as_posix(), (self.sidecar.root / LOOP_FILE).as_posix()))


# The fact turns the mode on and no setting does, so a setting can never disagree with where the Steering sits.
def sidecar_layer(top):
    try:
        sidecar = sidecar_of(Subprocess(), top)
    except Stop:
        return None
    return Layer(sidecar, "", SIDECAR) if (sidecar / LOOP_FILE).is_file() else None


def repo_steering_of(top):
    return RepoSteering(Layer(Path(top), "", REPO), sidecar_layer(top))

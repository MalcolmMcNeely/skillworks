# One reader, so preflight and the driver refuse the same loop file in the same words.

import json

from steering.target_branch import LOOP_FILE, SPEC_MODE, settings, target_setting
from stop import refusal

KEY = "export"


# The Export branch is read off the spec's own Target branch, so a named one leaves nothing to read.
def export_on(top):
    held = settings(top).get(KEY, False)
    if held is not True and held is not False:
        raise refusal("{} names export as {}. It can be true or false.".format(LOOP_FILE, json.dumps(held)))
    if held and target_setting(top) != SPEC_MODE:
        raise refusal("{} says export, and export works only with \"target-branch\": \"spec\", because each "
                      "spec's Target branch is named after the branch the Export writes onto.".format(LOOP_FILE))
    return held

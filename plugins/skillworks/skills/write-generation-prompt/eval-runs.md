# How each eval run runs

These rules hold for every eval run that `write-generation-prompt` or `write-judge-prompt` starts.

Use only the quick run the eval docs describe, and never a full run. A full run takes too long to repeat on each try.

Where the repo's own instructions limit eval runs, such as for loop work, those limits win over the quick run. Use the smaller run, and say in the report which instruction set it.

Where a run runs depends on how this Session started:

- **At the keyboard**, start each eval run in the background, and wait for its notification.
- **In a Session a script started**, such as a loop step, run each eval run in the foreground. A background command ends with the Session's last turn, so its result would be lost.

In a loop, the driver's words rule each "ask the person and wait" in the skill that sent you here.

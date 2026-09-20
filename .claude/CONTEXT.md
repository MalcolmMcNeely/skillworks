# Loop

How an agent is steered in this repository, and how a session is watched. Studio is the app, and
Architecture is the shape Studio's code keeps. This context is neither: it is the setup an agent runs
under, and the scripts that drive it.

## Language

**Land**:
A finished ticket reaching `main`. The driver rebases the ticket's worktree onto the newest `main`,
proves the work survived and the suite is green, then pushes. A ticket Lands on its own, the moment
it passes, so a stopped run leaves every ticket before it already on the remote.
_Avoid_: Integrate, integration

**Load**:
One instruction file reaching a session. It names the file, where it came from, when it came and why.
A Load is a fact about a session, never a judgement: a file that arrives when it should not have
still Loads. A memory file Claude Code wrote is a Load like any other. Its source is the machine and
not the repository, so two machines can Load different files at the same commit.
_Avoid_: Arrival, injection, attachment

**Session**:
One run of Claude Code, from the first prompt to the last. It carries an identity that every Load and
every telemetry event of that run shares, which is what lets the two be read together.
_Avoid_: Conversation, chat, transcript

# Loop

How an agent is steered in this repository, and how a session is watched. Studio is the app, and
Architecture is the shape Studio's code keeps. This context is neither: it is the setup an agent runs
under, and the scripts that drive it.

## Language

**Load**:
One instruction file reaching a session. It names the file, where it came from, when it came and why.
A Load is a fact about a session, never a judgement: a file that arrives when it should not have
still Loads.
_Avoid_: Arrival, injection, attachment

**Session**:
One run of Claude Code, from the first prompt to the last. It carries an identity that every Load and
every telemetry event of that run shares, which is what lets the two be read together.
_Avoid_: Conversation, chat, transcript

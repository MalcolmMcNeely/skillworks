namespace Skillworks.Core.Sessions.TimeBreakdown;

// Declaration order is the rank: the first part that was running takes the moment, so nothing counts twice.
// Hooks outrank Tools because a hook runs inside the Tool call it guards, and hook time is the reader's answer.
public enum Part
{
    Waiting,
    Hooks,
    Tools,
    Model,
    Subagents,
    Side,
    Quiet,
    YourTurn,
}

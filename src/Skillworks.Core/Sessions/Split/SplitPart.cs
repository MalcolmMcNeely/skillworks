namespace Skillworks.Core.Sessions.Split;

// Declaration order is the rank: the first part that was running takes the moment, so nothing counts twice.
// Hooks outrank Tools because a hook runs inside the Tool call it guards, and hook time is the reader's answer.
public enum SplitPart
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

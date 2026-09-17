namespace Skillworks.Core.Sessions.Findings;

// What counts as worth a person's attention is tuned here and nowhere else.
public static class Bars
{
    // Three goes at one call is an agent stuck in a loop; two is a retry that a person or a fix could still settle.
    public const int FailingAgain = 3;

    // Five passes over one file is an agent circling it, where four is a large change made in pieces.
    public const int EditedAgain = 5;

    public const int RateLimited = 1;

    // The cache is written at full price and read at a fraction of it, so rebuilding it once already costs money.
    public const int CacheRebuilt = 1;

    // Claude Code cuts a run down as its window fills, so a run this full is about to lose context.
    public const decimal NearTheLimit = 0.8m;

    // A hook is a guard around the work, and a run giving a sixth of its working time to guards is paying for them.
    public const decimal Hooks = 0.15m;

    // Two minutes of a run spent asking is the person's own delay, not the agent's.
    public const long WaitingMs = 120_000;

    // Three times what the others cost is a Subagent doing something other than what its siblings were asked to do.
    public const decimal CostlySubagent = 3m;
}

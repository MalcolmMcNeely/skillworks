namespace Skillworks.Core.Sessions.Findings;

public enum FindingKind
{
    FailingAgain,
    EditedAgain,
    RateLimited,
    CacheRebuilt,
    NearTheLimit,
    Hooks,
    Waiting,
    CostlySubagent,
}

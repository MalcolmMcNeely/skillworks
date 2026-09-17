using Skillworks.Core.EventsStore;
using Skillworks.Core.Sessions.Context;
using Skillworks.Core.Sessions.Exchanges;
using Skillworks.Core.Sessions.SkillCalls;
using Skillworks.Core.Sessions.Steps;

namespace Skillworks.Core.Sessions;

public sealed record OpenedRun(
    Session? Run,
    IReadOnlyList<Step> Steps,
    IReadOnlyList<Exchange> Said,
    IReadOnlyList<SkillCall> Fired,
    IReadOnlyList<ContextPoint> Sent,
    long? LimitTokens,
    EventLines Read);

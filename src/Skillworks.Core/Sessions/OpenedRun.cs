using Skillworks.Core.Sessions.Activations;
using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.Sessions.Context;
using Skillworks.Core.Sessions.Exchanges;
using Skillworks.Core.Sessions.Steps;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions;

public sealed record OpenedRun(
    Session? Run,
    IReadOnlyList<DrawnStep> Drawn,
    IReadOnlyList<Exchange> Said,
    IReadOnlyList<Activation> Fired,
    IReadOnlyList<ContextPoint> Sent,
    long? LimitTokens,
    IReadOnlyList<StepKey> Keys,
    IReadOnlyList<AgentCall> Called,
    // An answer or a tool result can be withheld too, and neither moves the Depth.
    bool PromptsWithheld,
    EventLines Read);

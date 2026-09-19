using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.Context;

public sealed record ContextPage(IReadOnlyList<ContextPoint> Points, long? LimitTokens) : ArrivingLine("context");

using Skillworks.Core.Arriving;

namespace Skillworks.Core.Sessions.Steps;

// Null where the store holds no run under that id, so a mistyped address says so instead of drawing an empty timeline.
public sealed record StepsHead(Session? Session) : ArrivingLine("head");

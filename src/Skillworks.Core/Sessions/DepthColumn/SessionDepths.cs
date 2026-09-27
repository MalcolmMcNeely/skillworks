using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.DepthColumn;

// A row this does not name has a Depth nobody could read, which is a dash and never Thin.
public sealed record SessionDepths(IReadOnlyDictionary<string, Depth> Depths) : ArrivingLine("depths");

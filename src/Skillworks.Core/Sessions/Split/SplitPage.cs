using Skillworks.Core.Arriving;
using Skillworks.Core.Filters;

namespace Skillworks.Core.Sessions.Split;

// Parts hold no moment twice and cover the whole run; Kinds overlap freely and read beside them.
public sealed record SplitPage(
    Depth Depth,
    IReadOnlyList<Spell> Parts,
    IReadOnlyList<Spell> Kinds) : ArrivingLine("split");

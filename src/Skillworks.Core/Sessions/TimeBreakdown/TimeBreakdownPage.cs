using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.TimeBreakdown;

// Parts hold no moment twice and cover the whole run; Kinds overlap freely and read beside them.
public sealed record TimeBreakdownPage(
    // Three of the Parts can only be measured from a Span, so without one they read not known and never zero.
    bool Traced,
    IReadOnlyList<PartSpell> Parts,
    IReadOnlyList<PartSpell> Kinds) : ArrivingLine("timeBreakdown");

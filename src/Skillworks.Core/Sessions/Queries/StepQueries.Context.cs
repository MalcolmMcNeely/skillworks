using Skillworks.Core.Sessions.Context;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Queries;

public sealed partial class StepQueries
{
    private const string InputAttribute = "input_tokens";

    private const string CacheReadAttribute = "cache_read_tokens";

    private const string CacheCreationAttribute = "cache_creation_tokens";

    // Enough of the context written again to cost real money, and most of it, so topping the cache up is no rebuild.
    private const long RebuiltTokens = 20_000;

    private const double RebuiltShare = 0.5;

    private static (IReadOnlyList<ContextPoint> Points, long? Limit) Sent(IReadOnlyList<EventLine> lines)
    {
        var turns =
            (from place in Enumerable.Range(0, lines.Count)
                let line = lines[place]
                where Named(TurnEvent)(line)
                select (Line: line, Id: Identity(line, place)))
            .ToList();

        return (
            [.. turns.Select((turn, order) => SentOn(turn.Line, turn.Id, order > 0))],
            ContextLimit.Stated(turns.Select(turn => turn.Line.Attribute(ModelAttribute))));
    }

    private static ContextPoint SentOn(EventLine line, string id, bool after)
    {
        var length = (long)Number(line, DurationAttribute);
        var written = (long)Number(line, CacheCreationAttribute);
        var tokens = (long)Number(line, InputAttribute) + (long)Number(line, CacheReadAttribute) + written;
        var skill = line.Attribute(EventAttributes.Skill);

        return new ContextPoint(
            id,
            line.At.AddMilliseconds(-length),
            length,
            tokens,
            written,
            skill == EventAttributes.Unnamed ? null : skill,
            skill == EventAttributes.Unnamed,
            // The first Turn of a run writes the whole cache, so only a later one can have rebuilt it.
            after && written >= RebuiltTokens && written > tokens * RebuiltShare);
    }
}

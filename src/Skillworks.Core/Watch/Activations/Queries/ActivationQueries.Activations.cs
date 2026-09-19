using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Shared.Provenance;
using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Watch.Activations.Queries;

public sealed partial class ActivationQueries
{
    // An Activation names the run it happened in, and a tally names none.
    public async Task<(IReadOnlyList<Activation> Fired, EventTotals Period)> ActivationsAsync(
        DaySpan span,
        Filter filter,
        CancellationToken cancellationToken)
    {
        var reading = events.LinesAsync(ActivationsIn(span, filter), cancellationToken);

        // Judged on the period, not on what was asked, or a Skill that never fired would read as a quiet week.
        var surveying = events.CountAsync(ActivationsIn(span), [], cancellationToken);

        var (read, period) = (await reading, await surveying);

        var fired =
            from line in read.Lines
            let skill = line.Attribute(EventAttributes.Skill)
            let session = line.Attribute(EventAttributes.Session)
            where skill is { Length: > 0 } && session is { Length: > 0 }
            // A skill author opens the run their Skill fired in most recently.
            orderby line.At descending
            select new Activation(skill, line.At, session, line.Repository, SkillOrigin.Of(line.Attribute).Trigger);

        return ([.. fired], period with { Unreachable = period.Unreachable ?? read.Unreachable });
    }
}

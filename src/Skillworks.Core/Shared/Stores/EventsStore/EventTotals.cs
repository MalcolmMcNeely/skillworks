namespace Skillworks.Core.Shared.Stores.EventsStore;

public sealed record EventTotals(IReadOnlyList<EventTotal> Groups, string? Unreachable)
{
    public decimal Total => Groups.Sum(group => group.Total);

    // An event that names no skill belongs to none, as Studio never guesses one.
    public IEnumerable<IGrouping<string, EventTotal>> BySkill() =>
        from total in Groups
        let skill = total.Attribute(EventAttributes.Skill)
        where skill is not null
        group total by skill;

    public EventTotals Plus(EventTotals other) => new([.. Groups, .. other.Groups], Unreachable ?? other.Unreachable);

    public static EventTotals Of(IReadOnlyList<EventTotal> groups) => new(groups, null);

    public static EventTotals Failed(string reason) => new([], reason);
}

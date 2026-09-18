using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed record FilterChoicesAnswer(IReadOnlyList<DateOnly> HeadDays, IReadOnlyList<FilterChoicesDayRow> Days)
{
    public static FilterChoicesAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        StudioHost.Read<DateOnly[]>(lines.Single(line => StudioHost.KindOf(line) == "head")["days"]),
        [.. lines.Where(line => StudioHost.KindOf(line) == "day").Select(StudioHost.Read<FilterChoicesDayRow>)]);

    public IEnumerable<string> Repositories => Days.SelectMany(day => day.Repositories);

    public FilterChoicesDayRow Day(DateOnly day) => Days.Single(landed => landed.Day == day);
}

using System.Globalization;
using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed record FilterChoicesAnswer(IReadOnlyList<DateOnly> HeadDays, IReadOnlyList<FilterChoicesDayRow> Days, GapRow Gap)
{
    public static FilterChoicesAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        StudioHost.Read<DateOnly[]>(lines.Single(line => StudioHost.KindOf(line) == "head")["days"]),
        [.. lines.Where(line => StudioHost.KindOf(line) == "day").Select(StudioHost.Read<FilterChoicesDayRow>)],
        StudioHost.Read<GapRow>(lines.Single(line => StudioHost.KindOf(line) == "end")["gap"]));

    public IEnumerable<string> Repositories => Days.SelectMany(day => day.Repositories);

    public FilterChoicesDayRow Day(string day) =>
        Days.Single(landed => landed.Day == DateOnly.Parse(day, CultureInfo.InvariantCulture));
}

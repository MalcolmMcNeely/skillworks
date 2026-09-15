using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed record SkillsAnswer(SkillsHeadRow Head, IReadOnlyList<SkillsDayRow> Days, GapRow Gap)
{
    public static SkillsAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        Read<SkillsHeadRow>(lines.Single(line => KindOf(line) == "head")),
        [.. lines.Where(line => KindOf(line) == "day").Select(Read<SkillsDayRow>)],
        Read<GapRow>(lines.Single(line => KindOf(line) == "end")["gap"]));

    public IEnumerable<SkillRow> Skills => Days.SelectMany(day => day.Skills);

    public static string? KindOf(JsonObject line) => (string?)line["kind"];

    public SkillsDayRow Day(string day) =>
        Days.Single(landed => landed.Day == DateOnly.Parse(day, CultureInfo.InvariantCulture));

    private static T Read<T>(JsonNode? line) =>
        line.Deserialize<T>(StudioHost.Wire) ?? throw new InvalidOperationException($"A {typeof(T).Name} came back empty.");
}

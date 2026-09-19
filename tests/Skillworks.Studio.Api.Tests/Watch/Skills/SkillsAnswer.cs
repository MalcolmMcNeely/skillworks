using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Shared.Gaps;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Watch.Skills;

public sealed record SkillsAnswer(SkillsHeadRow Head, IReadOnlyList<SkillsDayRow> Days, GapRow Gap)
{
    public static SkillsAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        StudioHost.Read<SkillsHeadRow>(lines.Single(line => StudioHost.KindOf(line) == "head")),
        [.. lines.Where(line => StudioHost.KindOf(line) == "day").Select(StudioHost.Read<SkillsDayRow>)],
        StudioHost.Read<GapRow>(lines.Single(line => StudioHost.KindOf(line) == "end")["gap"]));

    public IEnumerable<SkillRow> Skills => Days.SelectMany(day => day.Skills);

    public SkillsDayRow Day(DateOnly day) => Days.Single(landed => landed.Day == day);
}

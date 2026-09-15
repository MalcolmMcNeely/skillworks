using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed partial class ActivationEndpointsTests
{
    // More days than the test Loki lets one query cover.
    private const string TenDays = "?from=2026-09-01&to=2026-09-10";

    [Fact]
    public async Task Lists_each_firing_of_a_span_longer_than_one_query_may_cover_once_newest_first()
    {
        using var studio = new StudioHost();

        // One at every midnight, so wherever the span is cut, a firing sits on the cut.
        await studio.Push(SkillActivated.AtEveryMidnight("grilling", "2026-08-31", "2026-09-11"));

        var answer = await studio.ActivationList(TenDays);

        Assert.Equal("complete", answer.Gap.Kind);
        Assert.Equal(
            [.. Enumerable.Range(0, 10).Select(day => Moment("2026-09-10T00:00:00Z").AddDays(-day))],
            answer.Activations.Select(activation => activation.TimestampUtc));
    }

    [Fact]
    public async Task Keeps_the_newest_firings_of_a_span_longer_than_one_query_may_cover_when_it_holds_more_than_one_read_takes()
    {
        using var studio = new StudioHost(maxEvents: 2);

        // Days apart, so no one query holds all three.
        await studio.Push(
            new SkillActivated("grilling", "2026-09-01T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-05T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-10T09:00:00.000Z"));

        var answer = await studio.ActivationList(TenDays);

        Assert.Equal(
            [Moment("2026-09-10T09:00:00Z"), Moment("2026-09-05T09:00:00Z")],
            answer.Activations.Select(activation => activation.TimestampUtc));
        Assert.Equal("truncated", answer.Gap.Kind);
        Assert.Contains("newest 2", answer.Gap.Missing ?? "");
    }
}

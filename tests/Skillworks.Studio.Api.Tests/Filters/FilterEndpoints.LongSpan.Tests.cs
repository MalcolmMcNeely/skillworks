using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Filters;

public sealed partial class FilterEndpointsTests
{
    // More days than the test Loki lets one query cover.
    private const string TenDays = "?from=2026-09-01&to=2026-09-10";

    [Fact]
    public async Task Totals_a_span_longer_than_one_query_may_cover_as_if_it_were_one()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        // At both ends of the span, so no one query holds both.
        await studio.Push(
            new SkillActivated("grilling", "2026-09-01T09:00:00.000Z", Trigger: "claude-proactive", Owner: "acme", RepositoryName: "nu"),
            new SkillActivated("grilling", "2026-09-10T09:00:00.000Z", Trigger: "user-slash", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-10T09:05:00.000Z", Trigger: "user-slash", Owner: "acme", RepositoryName: "xi"));

        var answer = await studio.SkillTable(TenDays);
        var grilling = Assert.Single(answer.Skills);

        Assert.Equal("complete", answer.Provenance.Gap);
        Assert.Equal(3, grilling.Activations);
        Assert.Equal(["acme/nu", "acme/xi"], grilling.Repositories);
        Assert.Equal(["claude-proactive", "user-slash"], grilling.Origins.Select(origin => origin.Trigger).Order());
    }

    [Fact]
    public async Task Counts_a_firing_on_a_cut_between_queries_once()
    {
        using var studio = new StudioHost(StudioHost.Fixture("quiet"));

        // One at every midnight, so wherever the span is cut, a firing sits on the cut.
        await studio.Push(SkillActivated.AtEveryMidnight("grilling", "2026-08-31", "2026-09-11"));

        Assert.Equal(10, await studio.ActivationsOf("grilling", TenDays));
    }
}

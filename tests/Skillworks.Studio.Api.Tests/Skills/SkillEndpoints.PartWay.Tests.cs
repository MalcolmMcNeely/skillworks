using Skillworks.Core.EventsStore;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    private const string FiveDays = "?from=2026-09-11&to=2026-09-15";

    [Fact]
    public async Task Keeps_the_days_already_sent_and_ends_with_the_unreachable_Gap_when_the_store_fails_part_way()
    {
        using var events = BrokenEventsStore.DownBefore("2026-09-14");
        using var studio = new StudioHost(events: events);

        await studio.Push(
            new SkillActivated("grilling", "2026-09-15T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z"),
            new SkillActivated("grilling", "2026-09-13T09:00:00.000Z"));

        var lines = await studio.SkillLines(FiveDays);
        var answer = SkillsAnswer.Of(lines);

        Assert.Equal(["head", "day", "day", "end"], lines.Select(SkillsAnswer.KindOf));
        Assert.Equal([1, 2], answer.Days.Select(day => Assert.Single(day.Skills).Activations));
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    [Fact]
    public async Task Names_every_day_it_did_not_read_in_the_Gap()
    {
        using var events = BrokenEventsStore.DownBefore("2026-09-14");
        using var studio = new StudioHost(events: events);

        var missing = (await studio.SkillAnswer(FiveDays)).Gap.Missing ?? "";

        // The days that landed are whole, so only the rest are short.
        Assert.All(["2026-09-13", "2026-09-12", "2026-09-11"], day => Assert.Contains(day, missing));
        Assert.All(["2026-09-15", "2026-09-14"], day => Assert.DoesNotContain(day, missing));
    }

    [Fact]
    public async Task Asks_the_store_nothing_again_and_nothing_older_once_a_day_fails()
    {
        using var events = BrokenEventsStore.DownBefore("2026-09-14");
        using var studio = new StudioHost(events: events);

        await studio.SkillAnswer(FiveDays);

        // A retry asks again what was already asked.
        Assert.Equal(events.Asked.Distinct(), events.Asked);
        Assert.DoesNotContain(Day("2026-09-12"), events.DaysAsked);
    }

    [Fact]
    public async Task Lets_go_of_the_store_when_the_request_is_closed()
    {
        using var events = BrokenEventsStore.StallingBefore("2026-09-14");
        using var studio = new StudioHost(events: events);

        // Head and two days, then closed while the store holds the third, as when the Filter changes.
        await studio.SkillLines(FiveDays, count: 3);

        // The store's timeout lets go too, but only after Studio waited all of it.
        Assert.True(await events.HeldFor < TimeSpan.FromSeconds(new LokiOptions().TimeoutSeconds));
    }
}

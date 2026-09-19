using Skillworks.Core.Shared.Stores.EventsStore;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Skills;

public sealed partial class SkillEndpointsTests
{
    private static readonly string FiveDays = $"?from={Written(DaysBack(4))}&to={Written(Today)}";

    [Fact]
    public async Task Keeps_the_days_already_sent_and_ends_with_the_unreachable_Gap_when_the_store_fails_part_way()
    {
        using var events = BrokenEventsStore.DownBefore(Yesterday);
        using var studio = new StudioHost(events: events);

        await studio.Push(
            new SkillActivated("grilling", At(Today, "00:00:00.000")),
            new SkillActivated("grilling", At(Yesterday, "09:00:00.000")),
            new SkillActivated("grilling", At(Yesterday, "09:05:00.000")),
            new SkillActivated("grilling", At(DaysBack(2), "09:00:00.000")));

        var lines = await studio.SkillLines(FiveDays);
        var answer = SkillsAnswer.Of(lines);

        Assert.Equal(["head", "day", "day", "end"], lines.Select(StudioHost.KindOf));
        Assert.Equal([1, 2], answer.Days.Select(day => Assert.Single(day.Skills).Activations));
        Assert.Equal("unreachable", answer.Gap.Kind);
    }

    [Fact]
    public async Task Names_every_day_it_did_not_read_in_the_Gap()
    {
        using var events = BrokenEventsStore.DownBefore(Yesterday);
        using var studio = new StudioHost(events: events);

        var missing = (await studio.SkillAnswer(FiveDays)).Gap.Missing ?? "";

        // The days that landed are whole, so only the rest are short.
        Assert.All(
            [Written(DaysBack(2)), Written(DaysBack(3)), Written(DaysBack(4))],
            day => Assert.Contains(day, missing));
        Assert.All([Written(Today), Written(Yesterday)], day => Assert.DoesNotContain(day, missing));
    }

    [Fact]
    public async Task Asks_the_store_nothing_again_and_nothing_older_once_a_day_fails()
    {
        using var events = BrokenEventsStore.DownBefore(Yesterday);
        using var studio = new StudioHost(events: events);

        await studio.SkillAnswer(FiveDays);

        // A retry asks again what was already asked.
        Assert.Equal(events.Asked.Distinct(), events.Asked);
        Assert.DoesNotContain(DaysBack(3), events.DaysAsked);
    }

    [Fact]
    public async Task Lets_go_of_the_store_when_the_request_is_closed()
    {
        using var events = BrokenEventsStore.StallingBefore(Yesterday);
        using var studio = new StudioHost(events: events);

        // Head and two days, then closed while the store holds the third, as when the Filter changes.
        await studio.SkillLines(FiveDays, count: 3);

        // The store's timeout lets go too, but only after Studio waited all of it.
        Assert.True(await events.HeldFor < TimeSpan.FromSeconds(new LokiOptions().TimeoutSeconds));
    }
}

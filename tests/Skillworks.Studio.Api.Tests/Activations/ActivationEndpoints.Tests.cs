using System.Globalization;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Harness.StandIns;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed class ActivationEndpointsTests
{
    private const string Morning = "7c2b0d4a-0000-4000-8000-000000000001";

    private const string Afternoon = "7c2b0d4a-0000-4000-8000-000000000002";

    [Fact]
    public async Task Answers_with_the_activations_then_an_end()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", "2026-09-14T09:00:00.000Z", Morning));

        Assert.Equal(["activations", "end"], (await studio.ActivationLines("?skill=tdd")).Select(StudioHost.KindOf));
    }

    [Fact]
    public async Task Answers_with_lines_that_hold_only_what_a_screen_reads()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", "2026-09-14T09:00:00.000Z", Morning));

        var page = await studio.ActivationLine("activations", "?skill=tdd");

        Assert.Equal(["activations", "kind"], StudioHost.Fields(page));
        Assert.Equal(
            ["atUtc", "repository", "session", "skill", "trigger"],
            StudioHost.Fields(page["activations"]?[0]));
    }

    [Fact]
    public async Task Names_the_run_an_activation_happened_in_so_a_reader_can_open_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", "2026-09-14T09:00:00.000Z", Morning) with { Owner = "acme", RepositoryName = "xi", Trigger = "user-slash" });

        var activation = Assert.Single(await studio.ActivationsOf("?skill=tdd"));

        Assert.Equal("tdd", activation.Skill);
        Assert.Equal(Morning, activation.Session);
        Assert.Equal(Moment("2026-09-14T09:00:00.000Z"), activation.AtUtc);
        Assert.Equal("acme/xi", activation.Repository);
        Assert.Equal("user-slash", activation.Trigger);
    }

    [Fact]
    public async Task Lists_the_activations_newest_first()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", "2026-09-12T09:00:00.000Z", Morning),
            Fired("tdd", "2026-09-14T14:00:00.000Z", Afternoon));

        Assert.Equal([Afternoon, Morning], (await studio.ActivationsOf("?skill=tdd")).Select(activation => activation.Session));
    }

    [Fact]
    public async Task Lists_each_activation_of_a_skill_that_fired_twice_in_one_run()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", "2026-09-14T09:00:00.000Z", Morning),
            Fired("tdd", "2026-09-14T09:30:00.000Z", Morning));

        Assert.Equal(2, (await studio.ActivationsOf("?skill=tdd")).Count);
    }

    [Fact]
    public async Task Narrows_the_activations_to_the_skill_that_was_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", "2026-09-14T09:00:00.000Z", Morning),
            Fired("comment-sweep", "2026-09-14T09:30:00.000Z", Afternoon));

        Assert.Equal(["tdd"], (await studio.ActivationsOf("?skill=tdd")).Select(activation => activation.Skill));
    }

    [Fact]
    public async Task Narrows_the_activations_to_the_span_that_was_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", "2026-09-12T09:00:00.000Z", Morning),
            Fired("tdd", "2026-09-14T09:00:00.000Z", Afternoon));

        var activations = await studio.ActivationsOf("?skill=tdd&from=2026-09-14&to=2026-09-14");

        Assert.Equal([Afternoon], activations.Select(activation => activation.Session));
    }

    [Fact]
    public async Task Narrows_the_activations_to_the_repository_that_was_asked_for()
    {
        using var studio = new StudioHost();

        await studio.Push(
            Fired("tdd", "2026-09-14T09:00:00.000Z", Morning) with { Owner = "acme", RepositoryName = "xi" },
            Fired("tdd", "2026-09-14T09:30:00.000Z", Afternoon) with { Owner = "acme", RepositoryName = "nu" });

        Assert.Equal([Morning], (await studio.ActivationsOf("?skill=tdd&repository=acme/xi")).Select(activation => activation.Session));
    }

    [Fact]
    public async Task Names_no_repository_for_an_activation_in_a_checkout_that_has_none()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", "2026-09-14T09:00:00.000Z", Morning));

        Assert.Null(Assert.Single(await studio.ActivationsOf("?skill=tdd")).Repository);
    }

    [Fact]
    public async Task Answers_no_activations_for_a_skill_that_never_fired()
    {
        using var studio = new StudioHost();

        await studio.Push(Fired("tdd", "2026-09-14T09:00:00.000Z", Morning));

        var answer = await studio.ActivationAnswer("?skill=comment-sweep");

        // A skill that never fired must not read as a store that fell short.
        Assert.Empty(answer.Activations);
        Assert.Equal("complete", answer.Gap.Kind);
    }

    [Fact]
    public async Task Names_the_events_store_when_the_activations_cannot_be_read()
    {
        using var events = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: events);

        var answer = await studio.ActivationAnswer("?skill=tdd");

        Assert.Equal("unreachable", answer.Gap.Kind);
        Assert.NotNull(answer.Gap.Missing);
        Assert.Empty(answer.Activations);
    }

    private static SkillActivated Fired(string skill, string at, string session) =>
        new(skill, at) { Session = session };

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);
}

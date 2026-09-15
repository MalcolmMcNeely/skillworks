using System.Globalization;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed partial class ActivationEndpointsTests
{
    private const string BothDays = "?from=2026-09-01&to=2026-09-05";

    private const string GrilledAt = "2026-09-14T14:48:23.182Z";

    private const string Session = "0a9f1c2e-0000-4000-8000-000000000021";

    // No model, effort, branch or arguments: a skill_activated event carries none of them.
    private static readonly string[] EventFields = ["id", "origin", "repository", "sessionId", "skill", "timestampUtc"];

    [Fact]
    public async Task Lists_one_row_per_firing_in_the_span_newest_first()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-02T09:00:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("tdd", "2026-09-04T09:00:00.000Z", Trigger: "user-slash"),
            new SkillActivated("grilling", "2026-09-03T09:00:00.000Z", Trigger: "claude-proactive"),
            new SkillActivated("grilling", "2026-09-06T00:00:00.000Z", Trigger: "claude-proactive"));

        var listed = await studio.Activations(BothDays);

        // Newest first, because a reader opening a firing is nearly always looking for the last one.
        Assert.Equal(["tdd", "grilling", "grilling"], listed.Select(activation => activation.Skill));
        Assert.Equal(
            [Moment("2026-09-04T09:00:00Z"), Moment("2026-09-03T09:00:00Z"), Moment("2026-09-02T09:00:00Z")],
            listed.Select(activation => activation.TimestampUtc));
    }

    [Fact]
    public async Task Shows_the_skill_moment_origin_session_and_repository_its_event_recorded()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated(
            "grilling",
            GrilledAt,
            Trigger: "user-slash",
            Source: "plugin",
            Plugin: "probekit",
            Marketplace: "privateprobe",
            Owner: "acme",
            RepositoryName: "xi",
            Session: Session));

        var listed = Assert.Single(await studio.Activations());

        Assert.Equal("grilling", listed.Skill);
        Assert.Equal(Moment(GrilledAt), listed.TimestampUtc);
        Assert.Equal(Origin("user-slash", "plugin", "probekit", "privateprobe"), listed.Origin);
        Assert.Equal(Session, listed.SessionId);
        Assert.Equal("acme/xi", listed.Repository);
    }

    [Fact]
    public async Task Leaves_the_repository_of_a_firing_whose_event_named_none_unrecorded()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-14T09:05:00.000Z", RepositoryName: "xi"));

        var listed = await studio.Activations();

        // Half a name is no name: an older Claude Code or a repository with no origin remote is not a repository.
        Assert.Equal(2, listed.Count);
        Assert.All(listed, activation => Assert.Null(activation.Repository));
    }

    [Fact]
    public async Task Answers_with_nothing_an_event_does_not_carry()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        Assert.Equal(EventFields, await studio.ListedFields());
    }

    [Fact]
    public async Task Takes_each_firings_origin_from_its_own_event_and_never_from_one_beside_it()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T14:48:00.000Z", Trigger: "user-slash", Source: "userSettings"),
            new SkillActivated("grilling", "2026-09-14T14:48:30.000Z"));

        var listed = await studio.Activations();

        // Thirty seconds apart, the same skill: a firing that recorded no trigger does not borrow its neighbour's.
        Assert.Equal([null, "user-slash"], listed.Select(activation => activation.Origin.Trigger));
        Assert.Equal([null, "userSettings"], listed.Select(activation => activation.Origin.Source));
    }

    [Fact]
    public async Task Narrows_the_list_by_the_span_the_repository_and_the_skill_at_once()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-05T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-05T09:05:00.000Z", Owner: "acme", RepositoryName: "nu"),
            new SkillActivated("grilling", "2026-09-05T09:10:00.000Z"),
            new SkillActivated("tdd", "2026-09-05T09:15:00.000Z", Owner: "acme", RepositoryName: "xi"),
            new SkillActivated("grilling", "2026-09-06T09:00:00.000Z", Owner: "acme", RepositoryName: "xi"));

        var listed = await studio.Activations("?from=2026-09-05&to=2026-09-05&repository=acme/xi&skill=grilling");

        var only = Assert.Single(listed);
        Assert.Equal(Moment("2026-09-05T09:00:00Z"), only.TimestampUtc);
    }

    [Fact]
    public async Task Covers_the_lookback_when_the_filter_names_no_span()
    {
        using var studio = new StudioHost();

        await studio.Push(
            new SkillActivated("grilling", "2026-09-08T23:59:59.999Z"),
            new SkillActivated("grilling", "2026-09-09T00:00:00.000Z"),
            new SkillActivated("grilling", "2026-09-15T09:00:00.000Z"));

        var answer = await studio.ActivationList("?skill=grilling");

        // Today and the six UTC days before it, as the skill table counts, so a row count matches its activations.
        Assert.Equal(
            [Moment("2026-09-15T09:00:00Z"), Moment("2026-09-09T00:00:00Z")],
            answer.Activations.Select(activation => activation.TimestampUtc));
        Assert.Equal(Span("2026-09-09", "2026-09-15", lookback: true), answer.Span);
    }

    [Fact]
    public async Task Names_the_span_a_filter_gave_in_place_of_the_lookback()
    {
        using var studio = new StudioHost();

        var answer = await studio.ActivationList(BothDays);

        // Named in the answer, so an empty list says which days it is empty for.
        Assert.Equal(Span("2026-09-01", "2026-09-05", lookback: false), answer.Span);
    }

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);

    private static SpanRow Span(string from, string to, bool lookback) => new()
    {
        From = DateOnly.Parse(from, CultureInfo.InvariantCulture),
        To = DateOnly.Parse(to, CultureInfo.InvariantCulture),
        Lookback = lookback,
    };

    private static OriginRow Origin(string? trigger, string? source, string? plugin, string? marketplace) => new()
    {
        Trigger = trigger,
        Source = source,
        Plugin = plugin,
        Marketplace = marketplace,
    };
}

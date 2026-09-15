using System.Net;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed partial class ActivationEndpointsTests
{
    private const string OtherSession = "0a9f1c2e-0000-4000-8000-000000000022";

    [Fact]
    public async Task Opens_one_activation_by_the_id_the_list_gave_for_it()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated(
            "grilling",
            GrilledAt,
            Trigger: "claude-proactive",
            Source: "projectSettings",
            Owner: "acme",
            RepositoryName: "xi",
            Session: Session));

        var listed = Assert.Single(await studio.Activations());
        var opened = await studio.Activation(listed.Id);

        Assert.Equal(listed, opened);
    }

    [Fact]
    public async Task Opens_the_same_firing_every_time_however_close_the_firings_beside_it()
    {
        using var studio = new StudioHost();

        // A millisecond apart, one skill: only the session and the sequence tell these three apart.
        await studio.Push(
            new SkillActivated("grilling", "2026-09-14T09:00:00.000Z", Trigger: "claude-proactive", Session: Session, Sequence: 7),
            new SkillActivated("grilling", "2026-09-14T09:00:00.001Z", Trigger: "user-slash", Session: OtherSession, Sequence: 7),
            new SkillActivated("grilling", "2026-09-14T09:00:00.002Z", Trigger: "nested-skill", Session: Session, Sequence: 8));

        var listed = await studio.Activations();
        var firstOpened = await Task.WhenAll(listed.Select(activation => studio.Activation(activation.Id)));

        await studio.Push(new SkillActivated("grilling", "2026-09-14T09:00:00.500Z", Trigger: "agent-preload", Session: Session, Sequence: 9));

        var openedAgain = await Task.WhenAll(listed.Select(activation => studio.Activation(activation.Id)));

        Assert.Equal(["nested-skill", "user-slash", "claude-proactive"], firstOpened.Select(opened => opened.Origin.Trigger));
        Assert.Equal(listed, firstOpened);
        Assert.Equal(listed, openedAgain);
    }

    [Fact]
    public async Task Opens_a_firing_from_long_before_the_lookback()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", "2026-08-01T09:00:00.000Z", Trigger: "claude-proactive"));

        var listed = Assert.Single(await studio.Activations("?from=2026-08-01&to=2026-08-01"));

        // A shared link is not narrowed by the filter or the week it was shared in.
        Assert.Equal(listed, await studio.Activation(listed.Id));
    }

    [Fact]
    public async Task Answers_nothing_on_the_page_an_event_does_not_carry()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var listed = Assert.Single(await studio.Activations());

        Assert.Equal(EventFields, await studio.OpenedFields(listed.Id));
    }

    [Fact]
    public async Task Answers_an_activation_it_cannot_find_with_a_not_found()
    {
        using var studio = new StudioHost();

        await studio.Push(new SkillActivated("grilling", GrilledAt, Session: Session));

        var listed = Assert.Single(await studio.Activations());

        using var unshaped = await studio.AskForActivation("toolu_no_such_firing");
        using var elsewhere = await studio.AskForActivation(listed.Id.Replace(Session, OtherSession));

        // Missing, not empty: a blank page would read as a firing that happened and carried nothing.
        Assert.Equal(HttpStatusCode.NotFound, unshaped.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, elsewhere.StatusCode);
    }

    [Fact]
    public async Task Says_the_events_store_could_not_be_read_rather_than_that_a_firing_does_not_exist()
    {
        using var sent = new StudioHost();
        using var down = BrokenEventsStore.Down();
        using var studio = new StudioHost(events: down);

        await sent.Push(new SkillActivated("grilling", GrilledAt));

        var listed = Assert.Single(await sent.Activations());
        var opened = await studio.OpenActivation(listed.Id);

        // A not found here would tell a reader with a good link that the firing never happened.
        Assert.Null(opened.Activation);
        Assert.Equal("unreachable", opened.Gap.Kind);
    }

    [Fact]
    public async Task Reports_an_events_store_that_answers_a_page_badly_as_unreachable()
    {
        using var sent = new StudioHost();
        using var failing = BrokenEventsStore.Failing(HttpStatusCode.BadGateway);
        using var studio = new StudioHost(events: failing);

        await sent.Push(new SkillActivated("grilling", GrilledAt));

        var listed = Assert.Single(await sent.Activations());
        var opened = await studio.OpenActivation(listed.Id);

        Assert.Null(opened.Activation);
        Assert.Equal("unreachable", opened.Gap.Kind);
        Assert.Contains("502", opened.Gap.Missing ?? "");
    }

    [Fact]
    public async Task Says_telemetry_is_off_beside_one_firing_as_well_as_beside_the_list()
    {
        using var studio = new StudioHost(emitting: false);

        await studio.Push(new SkillActivated("grilling", GrilledAt, Trigger: "claude-proactive"));

        var listed = Assert.Single(await studio.Activations());
        var opened = await studio.OpenActivation(listed.Id);

        // The firing is real, but nothing has reached the events store since the switch went off.
        Assert.Equal(listed, opened.Activation);
        Assert.Equal("telemetryOff", opened.Gap.Kind);
    }
}

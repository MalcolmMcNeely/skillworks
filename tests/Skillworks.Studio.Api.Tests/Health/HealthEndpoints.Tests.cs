using System.Net;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Skills;

namespace Skillworks.Studio.Api.Tests.Health;

public sealed class HealthEndpointsTests
{
    [Fact]
    public async Task Reports_every_part_of_studio_in_one_answer()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue());

        // Ordered here and not in the report. Which parts are covered is the answer; the order they
        // are listed in is a choice about the screen, and a test that pinned it would break on a
        // rearrangement that changed nothing a reader could observe.
        var parts = (await studio.Health()).Parts.Select(part => part.Name).Order();

        // A part missing from here is a part a developer has to go and check by hand.
        Assert.Equal(
            ["Catalogue", "Claude Code telemetry", "Events store", "Transcript store", "Transcripts"],
            parts);
    }

    [Fact]
    public async Task Says_every_part_is_working_and_leaves_nothing_to_do_when_nothing_is_wrong()
    {
        // A fixture with nothing in it the ingest has to step over, so "nothing to do" means the
        // whole of Studio is healthy rather than only most of it.
        using var studio = new StudioHost(StudioHost.Fixture("quiet"), StudioHost.Catalogue());

        var health = await studio.Health();

        Assert.All(health.Parts, part => Assert.Equal("working", part.State));
        Assert.All(health.Parts, part => Assert.Null(part.Action));
        Assert.Null(health.WhyEmpty);
    }

    [Fact]
    public async Task Says_what_the_ingest_stepped_over_and_where_to_go_and_read_it()
    {
        using var studio = new StudioHost(StudioHost.Fixture("malformed"), StudioHost.Catalogue());

        var part = await studio.Part("Transcript store");

        // Still working: a fault is a gap in the numbers, not a broken store. The count is here so
        // a total that looks low is explained rather than trusted.
        Assert.Equal("working", part.State);
        Assert.Contains("could not parse", part.Detail);
        Assert.Contains("ingest panel", part.Action ?? "");
    }

    [Fact]
    public async Task Says_it_cannot_tell_whether_telemetry_is_on_when_it_cannot_read_the_settings()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), settings: "{ not json");

        var part = await studio.Part("Claude Code telemetry");

        // Broken, not off. Studio does not know whether the switch was ever flipped, and a panel
        // that guessed "off" would send a developer to write a file Studio has already refused.
        Assert.Equal("broken", part.State);
        Assert.Contains("cannot read", part.Detail);
    }

    [Fact]
    public async Task Reports_an_events_store_that_is_down_as_broken_and_says_how_to_start_it()
    {
        using var events = Events.Down();
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), events: events);

        var part = await studio.Part("Events store");

        Assert.Equal("broken", part.State);
        Assert.Contains("aspire run", part.Action ?? "");
    }

    [Fact]
    public async Task Reports_an_events_store_that_answers_badly_as_broken_too()
    {
        using var events = Events.Failing(HttpStatusCode.BadGateway);
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), events: events);

        var part = await studio.Part("Events store");

        // Asked directly rather than inferred from an empty list of events, so a store that is up
        // and unhappy cannot be read as a store with nothing in it.
        Assert.Equal("broken", part.State);
        Assert.Contains("502", part.Detail);
    }

    [Fact]
    public async Task Reports_telemetry_that_was_never_switched_on_as_off_rather_than_as_broken()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), emitting: false);

        var part = await studio.Part("Claude Code telemetry");

        // A switch nobody flipped is not a fault. Reporting it as one would send a developer
        // looking for a container problem that does not exist.
        Assert.Equal("off", part.State);
        Assert.Contains("Telemetry panel", part.Action ?? "");
    }

    [Fact]
    public async Task Tells_a_store_that_is_down_apart_from_telemetry_that_is_switched_off()
    {
        using var down = Events.Down();
        using var quiet = Events.Holding();
        using var broken = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), events: down);
        using var off = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), events: quiet, emitting: false);

        var outage = await broken.Health();
        var never = await off.Health();

        // The same screen goes empty either way. The two states differ in which part is at fault
        // and in what a developer does next, and both are here to be read.
        Assert.Equal("broken", outage.Parts.Single(part => part.Name == "Events store").State);
        Assert.Equal("working", outage.Parts.Single(part => part.Name == "Claude Code telemetry").State);

        Assert.Equal("working", never.Parts.Single(part => part.Name == "Events store").State);
        Assert.Equal("off", never.Parts.Single(part => part.Name == "Claude Code telemetry").State);
    }

    [Fact]
    public async Task Keeps_the_transcript_half_healthy_when_the_containers_are_down()
    {
        using var events = Events.Down();
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), events: events);

        var health = await studio.Health();

        // The transcripts are the durable record and owe the containers nothing. A docker problem
        // costs the provenance view and not the app.
        Assert.Equal("working", health.Parts.Single(part => part.Name == "Transcripts").State);
        Assert.Equal("working", health.Parts.Single(part => part.Name == "Transcript store").State);
        Assert.Null(health.WhyEmpty);
        Assert.NotEmpty(await studio.Skills());
    }

    [Fact]
    public async Task Names_the_missing_transcript_folder_and_the_setting_that_points_at_it()
    {
        using var studio = new StudioHost("no-such-folder", StudioHost.Catalogue());

        var health = await studio.Health();
        var part = health.Parts.Single(p => p.Name == "Transcripts");

        Assert.Equal("broken", part.State);
        Assert.Contains("Transcripts:Path", part.Action ?? "");

        // The same fact again as the reason a view is empty, so a screen with no rows on it can say
        // which source is missing without a reader going looking for the panel that knows.
        Assert.Contains("no folder", health.WhyEmpty ?? "");
        Assert.Contains("Transcripts:Path", health.WhyEmpty ?? "");
    }

    [Fact]
    public async Task Blames_an_empty_folder_on_the_folder_rather_than_on_the_history()
    {
        using var folder = new TemporaryFolder();
        using var studio = new StudioHost(folder.Subfolder("no-sessions"), StudioHost.Catalogue());

        var health = await studio.Health();

        // The folder is there and holds nothing. Studio is healthy, and a reader still needs to be
        // told the difference between "no skill has ever fired" and "there is nothing to read".
        Assert.Equal("working", health.Parts.Single(part => part.Name == "Transcripts").State);
        Assert.Contains("no transcripts in", health.WhyEmpty ?? "");
    }

    [Fact]
    public async Task Names_the_missing_catalogue_and_what_it_costs()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"));

        var part = await studio.Part("Catalogue");

        Assert.Equal("broken", part.State);
        Assert.Contains("Catalogue:Path", part.Action ?? "");

        // A missing catalogue empties no view, so it is not the reason a table has no rows in it.
        Assert.Null((await studio.Health()).WhyEmpty);
    }
}

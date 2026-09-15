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

        // Sorted here, because the report's order is the screen's choice and not part of the answer.
        var parts = (await studio.Health()).Parts.Select(part => part.Name).Order();

        // A part missing from here is a part a developer has to go and check by hand.
        Assert.Equal(
            ["Catalogue", "Claude Code telemetry", "Events store", "Transcript store", "Transcripts"],
            parts);
    }

    [Fact]
    public async Task Says_every_part_is_working_and_leaves_nothing_to_do_when_nothing_is_wrong()
    {
        // A fixture with nothing for the ingest to step over, so "nothing to do" means all of Studio is healthy.
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

        // Still working: a fault is a gap in the numbers, not a broken store, and the count explains a low total.
        Assert.Equal("working", part.State);
        Assert.Contains("could not parse", part.Detail);
        Assert.Contains("ingest panel", part.Action ?? "");
    }

    [Fact]
    public async Task Says_it_cannot_tell_whether_telemetry_is_on_when_it_cannot_read_the_settings()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), settings: "{ not json");

        var part = await studio.Part("Claude Code telemetry");

        // Broken, not off: a panel that guessed "off" would send a developer to write a file Studio has refused.
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

        // Asked directly, so an events store that is up and unhappy never reads as one with nothing in it.
        Assert.Equal("broken", part.State);
        Assert.Contains("502", part.Detail);
    }

    [Fact]
    public async Task Reports_telemetry_that_was_never_switched_on_as_off_rather_than_as_broken()
    {
        using var studio = new StudioHost(StudioHost.Fixture("ordinary"), StudioHost.Catalogue(), emitting: false);

        var part = await studio.Part("Claude Code telemetry");

        // Not a fault: reporting one would send a developer after a container problem that does not exist.
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

        // The same screen goes empty either way, but the part at fault and the developer's next step differ.
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

        // The transcripts owe the containers nothing, so a docker problem costs the provenance view, not the app.
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

        // Repeated as the reason a view is empty, so an empty screen names the missing source itself.
        Assert.Contains("no folder", health.WhyEmpty ?? "");
        Assert.Contains("Transcripts:Path", health.WhyEmpty ?? "");
    }

    [Fact]
    public async Task Blames_an_empty_folder_on_the_folder_rather_than_on_the_history()
    {
        using var folder = new TemporaryFolder();
        using var studio = new StudioHost(folder.Subfolder("no-sessions"), StudioHost.Catalogue());

        var health = await studio.Health();

        // Healthy, but a reader must still tell "no skill has fired" from "there is nothing to read".
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

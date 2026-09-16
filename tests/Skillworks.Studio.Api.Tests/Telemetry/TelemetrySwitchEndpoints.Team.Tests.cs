using System.Net;
using System.Net.Http.Json;
using System.Text.Json;

namespace Skillworks.Studio.Api.Tests.Telemetry;

public sealed partial class TelemetrySwitchEndpointsTests
{
    [Fact]
    public async Task Names_the_repository_file_a_team_would_commit_to_switch_everyone_on()
    {
        using var studio = new TelemetrySwitchHost("{}");

        var team = (await studio.State()).GetProperty("team");

        Assert.Equal(".claude/settings.json", team.GetProperty("path").GetString());
    }

    [Fact]
    public async Task Shows_the_team_file_holding_every_setting_the_switch_writes()
    {
        using var studio = new TelemetrySwitchHost("{}");

        var environment = TelemetrySwitchHost.TeamEnvironment(await studio.State());

        Assert.All(Owned, variable => Assert.Equal(variable.Value, environment.GetProperty(variable.Key).GetString()));
    }

    [Fact]
    public async Task Points_the_team_file_at_the_collector_address_studio_was_configured_with()
    {
        using var studio = new TelemetrySwitchHost("{}");

        var environment = TelemetrySwitchHost.TeamEnvironment(await studio.State());

        Assert.Equal(TelemetrySwitchHost.Collector, environment.GetProperty("OTEL_EXPORTER_OTLP_ENDPOINT").GetString());
    }

    [Fact]
    public async Task Shows_the_team_file_without_ever_writing_one()
    {
        using var studio = new TelemetrySwitchHost("{}");

        var path = (await studio.State()).GetProperty("team").GetProperty("path").GetString()!;
        await studio.Turn(emitting: true);

        Assert.False(File.Exists(Path.Combine(Directory.GetCurrentDirectory(), path)));
        Assert.Equal([studio.SettingsName(), TelemetrySwitchHost.StampName], studio.FilesWritten());
    }

    [Fact]
    public async Task Writes_the_machine_it_runs_on_even_when_the_call_names_another_file()
    {
        using var studio = new TelemetrySwitchHost("{}");
        var elsewhere = studio.Beside("someone-else.json");

        using var response = await studio.Client.PutAsJsonAsync(
            "/api/telemetry/switch",
            new { emitting = true, settingsPath = elsewhere },
            TelemetrySwitchHost.Wire);

        response.EnsureSuccessStatusCode();
        Assert.False(File.Exists(elsewhere));
        Assert.Equal("otlp", studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    [Fact]
    public async Task Offers_no_way_to_write_the_team_file()
    {
        using var studio = new TelemetrySwitchHost("{}");

        using var response = await studio.Client.PutAsJsonAsync("/api/telemetry/team", new { }, TelemetrySwitchHost.Wire);

        Assert.Equal(HttpStatusCode.NotFound, response.StatusCode);
    }

    [Fact]
    public async Task Reads_the_team_file_back_as_a_settings_document_claude_code_would_accept()
    {
        using var studio = new TelemetrySwitchHost("{}");

        var text = (await studio.State()).GetProperty("team").GetProperty("text").GetString()!;
        using var document = JsonDocument.Parse(text);

        Assert.Equal(["env"], document.RootElement.EnumerateObject().Select(field => field.Name));
    }
}

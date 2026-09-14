using System.Net;
using System.Text.Json.Nodes;

namespace Skillworks.Studio.Api.Tests.Telemetry;

public sealed class TelemetrySwitchEndpointsTests
{
    // Not shared with the code under test, so a rename has to be made twice on purpose.
    private static readonly string[] Owned =
    [
        "CLAUDE_CODE_ENABLE_TELEMETRY",
        "OTEL_LOGS_EXPORTER",
        "OTEL_LOG_TOOL_DETAILS",
        "OTEL_EXPORTER_OTLP_PROTOCOL",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
    ];

    [Fact]
    public async Task Reports_telemetry_off_when_there_is_no_settings_file()
    {
        using var studio = new TelemetryStudio();

        var state = await studio.State();

        Assert.False(state.GetProperty("emitting").GetBoolean());
        Assert.True(state.GetProperty("readable").GetBoolean());
    }

    [Fact]
    public async Task Reports_telemetry_off_when_the_settings_hold_no_telemetry_variables()
    {
        using var studio = new TelemetryStudio("""{ "model": "opus", "env": { "PAGER": "less" } }""");

        var state = await studio.State();

        Assert.False(state.GetProperty("emitting").GetBoolean());
    }

    [Fact]
    public async Task Reports_telemetry_on_once_the_switch_has_written_the_variables()
    {
        using var studio = new TelemetryStudio("{}");

        await studio.Turn(emitting: true);
        var state = await studio.State();

        Assert.True(state.GetProperty("emitting").GetBoolean());
        Assert.Empty(state.GetProperty("changes").EnumerateArray());
    }

    [Fact]
    public async Task Shows_every_variable_it_would_write_before_it_writes_anything()
    {
        using var studio = new TelemetryStudio("{}");

        var changes = TelemetryStudio.Changes(await studio.State());

        Assert.Equal(Owned.Order(), changes.Keys.Order());
        Assert.Equal("{}", studio.SettingsText());
    }

    [Fact]
    public async Task Names_the_value_it_would_displace_so_the_preview_is_the_whole_change()
    {
        using var studio = new TelemetryStudio(
            """{ "env": { "OTEL_LOGS_EXPORTER": "console" } }""");

        var state = await studio.State();
        var change = state.GetProperty("changes")
            .EnumerateArray()
            .Single(entry => entry.GetProperty("name").GetString() == "OTEL_LOGS_EXPORTER");

        Assert.Equal("console", change.GetProperty("from").GetString());
        Assert.Equal("otlp", change.GetProperty("to").GetString());
    }

    [Fact]
    public async Task Says_a_session_already_running_will_not_pick_the_change_up()
    {
        using var studio = new TelemetryStudio("{}");

        var note = (await studio.State()).GetProperty("restartNote").GetString();

        Assert.Contains("restart", note!, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Points_the_settings_at_the_collector_address_it_was_configured_with()
    {
        using var studio = new TelemetryStudio("{}");

        await studio.Turn(emitting: true);

        Assert.Equal(TelemetryStudio.Collector, studio.Variable("OTEL_EXPORTER_OTLP_ENDPOINT"));
        Assert.Equal(
            TelemetryStudio.Collector,
            (await studio.State()).GetProperty("collectorEndpoint").GetString());
    }

    [Fact]
    public async Task Writes_the_variables_that_make_the_skill_name_arrive_unredacted()
    {
        using var studio = new TelemetryStudio("{}");

        await studio.Turn(emitting: true);

        Assert.Equal("1", studio.Variable("CLAUDE_CODE_ENABLE_TELEMETRY"));
        Assert.Equal("otlp", studio.Variable("OTEL_LOGS_EXPORTER"));
        Assert.Equal("1", studio.Variable("OTEL_LOG_TOOL_DETAILS"));
        Assert.Equal("http/protobuf", studio.Variable("OTEL_EXPORTER_OTLP_PROTOCOL"));
    }

    [Fact]
    public async Task Creates_a_settings_file_when_the_developer_has_none()
    {
        using var studio = new TelemetryStudio();

        await studio.Turn(emitting: true);

        Assert.True(studio.SettingsExist());
        Assert.Equal("otlp", studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    [Fact]
    public async Task Leaves_the_model_theme_and_status_line_alone_when_turning_on()
    {
        using var studio = new TelemetryStudio(
            """
            {
              "model": "opus",
              "theme": "dark",
              "statusLine": { "type": "command", "command": "mine.sh" }
            }
            """);

        await studio.Turn(emitting: true);
        var settings = studio.Settings();

        Assert.Equal("opus", settings.GetProperty("model").GetString());
        Assert.Equal("dark", settings.GetProperty("theme").GetString());
        Assert.Equal("mine.sh", settings.GetProperty("statusLine").GetProperty("command").GetString());
    }

    [Fact]
    public async Task Keeps_environment_variables_it_does_not_own()
    {
        using var studio = new TelemetryStudio("""{ "env": { "PAGER": "less" } }""");

        await studio.Turn(emitting: true);

        Assert.Equal("less", studio.Variable("PAGER"));
    }

    [Fact]
    public async Task Refuses_to_write_over_settings_it_cannot_parse()
    {
        const string broken = """{ "model": "opus", """;
        using var studio = new TelemetryStudio(broken);

        using var response = await studio.Flip(emitting: true);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(broken, studio.SettingsText());
        Assert.False((await studio.State()).GetProperty("readable").GetBoolean());
    }

    [Fact]
    public async Task Refuses_to_write_over_settings_whose_root_is_not_an_object()
    {
        const string list = """["not", "a", "settings", "document"]""";
        using var studio = new TelemetryStudio(list);

        using var response = await studio.Flip(emitting: true);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(list, studio.SettingsText());
    }

    [Fact]
    public async Task Refuses_to_write_when_the_environment_block_is_not_an_object()
    {
        const string odd = """{ "env": "everything" }""";
        using var studio = new TelemetryStudio(odd);

        using var response = await studio.Flip(emitting: true);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(odd, studio.SettingsText());
        Assert.False((await studio.State()).GetProperty("readable").GetBoolean());
    }

    [Fact]
    public async Task Turning_off_removes_only_the_variables_it_added()
    {
        using var studio = new TelemetryStudio("""{ "model": "opus", "env": { "PAGER": "less" } }""");

        await studio.Turn(emitting: true);
        var state = await studio.Turn(emitting: false);

        Assert.False(state.GetProperty("emitting").GetBoolean());
        Assert.All(Owned, name => Assert.Null(studio.Variable(name)));
        Assert.Equal("less", studio.Variable("PAGER"));
        Assert.Equal("opus", studio.Settings().GetProperty("model").GetString());
    }

    [Fact]
    public async Task Turning_off_puts_back_a_value_it_displaced()
    {
        using var studio = new TelemetryStudio(
            """{ "env": { "OTEL_LOGS_EXPORTER": "console", "OTEL_EXPORTER_OTLP_ENDPOINT": "http://elsewhere:4318" } }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.Equal("console", studio.Variable("OTEL_LOGS_EXPORTER"));
        Assert.Equal("http://elsewhere:4318", studio.Variable("OTEL_EXPORTER_OTLP_ENDPOINT"));
    }

    [Fact]
    public async Task Turning_off_keeps_a_variable_the_developer_had_already_set_the_same_way()
    {
        using var studio = new TelemetryStudio(
            """{ "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1" } }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.Equal("1", studio.Variable("CLAUDE_CODE_ENABLE_TELEMETRY"));
        Assert.Null(studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    [Fact]
    public async Task Turning_off_leaves_a_variable_the_developer_has_since_changed()
    {
        using var studio = new TelemetryStudio("{}");

        await studio.Turn(emitting: true);
        Rewrite(studio, "OTEL_EXPORTER_OTLP_ENDPOINT", "http://mine:4318");
        await studio.Turn(emitting: false);

        Assert.Equal("http://mine:4318", studio.Variable("OTEL_EXPORTER_OTLP_ENDPOINT"));
        Assert.Null(studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    [Fact]
    public async Task Turning_off_takes_away_an_environment_block_it_created_itself()
    {
        using var studio = new TelemetryStudio("""{ "model": "opus" }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.False(studio.Settings().TryGetProperty("env", out _));
    }

    [Fact]
    public async Task Turning_off_keeps_an_environment_block_the_developer_already_had()
    {
        using var studio = new TelemetryStudio("""{ "env": {} }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.True(studio.Settings().TryGetProperty("env", out _));
    }

    [Fact]
    public async Task Turning_off_when_there_is_no_settings_file_writes_nothing()
    {
        using var studio = new TelemetryStudio();

        await studio.Turn(emitting: false);

        Assert.False(studio.SettingsExist());
    }

    [Fact]
    public async Task Turning_on_twice_leaves_the_same_settings_as_turning_on_once()
    {
        using var studio = new TelemetryStudio("""{ "env": { "OTEL_LOGS_EXPORTER": "console" } }""");

        await studio.Turn(emitting: true);
        var once = studio.SettingsText();
        await studio.Turn(emitting: true);

        Assert.Equal(once, studio.SettingsText());

        // The displaced value has to survive the second write, or the undo is lost.
        await studio.Turn(emitting: false);
        Assert.Equal("console", studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    private static void Rewrite(TelemetryStudio studio, string name, string value)
    {
        var settings = JsonNode.Parse(studio.SettingsText())!;
        settings["env"]![name] = value;

        studio.RewriteSettings(settings.ToJsonString());
    }
}

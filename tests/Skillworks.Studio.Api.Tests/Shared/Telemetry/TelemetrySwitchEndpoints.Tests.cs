using System.Net;
using System.Text.Json.Nodes;

namespace Skillworks.Studio.Api.Tests.Shared.Telemetry;

public sealed partial class TelemetrySwitchEndpointsTests
{
    private const string RepositoryVariable = "OTEL_METRICS_INCLUDE_REPOSITORY";

    // Not shared with the code under test, so a rename has to be made twice on purpose.
    private static readonly Dictionary<string, string> Owned = new()
    {
        ["CLAUDE_CODE_ENABLE_TELEMETRY"] = "1",
        ["OTEL_LOGS_EXPORTER"] = "otlp",
        ["OTEL_LOG_TOOL_DETAILS"] = "1",
        ["OTEL_EXPORTER_OTLP_PROTOCOL"] = "http/protobuf",
        ["OTEL_EXPORTER_OTLP_ENDPOINT"] = TelemetrySwitchHost.Collector,
        [RepositoryVariable] = "true",
        ["OTEL_LOG_USER_PROMPTS"] = "1",
        ["OTEL_LOG_ASSISTANT_RESPONSES"] = "1",
        ["OTEL_LOG_TOOL_CONTENT"] = "1",
        ["CLAUDE_CODE_ENHANCED_TELEMETRY_BETA"] = "1",
        ["OTEL_TRACES_EXPORTER"] = "otlp",
    };

    [Fact]
    public async Task Reports_telemetry_off_when_there_is_no_settings_file()
    {
        using var studio = new TelemetrySwitchHost();

        var state = await studio.State();

        Assert.False(state.GetProperty("emitting").GetBoolean());
        Assert.True(state.GetProperty("readable").GetBoolean());
    }

    [Fact]
    public async Task Reports_telemetry_off_when_the_settings_hold_no_telemetry_variables()
    {
        using var studio = new TelemetrySwitchHost("""{ "model": "opus", "env": { "PAGER": "less" } }""");

        var state = await studio.State();

        Assert.False(state.GetProperty("emitting").GetBoolean());
    }

    [Fact]
    public async Task Reports_telemetry_on_once_the_switch_has_written_the_variables()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);
        var state = await studio.State();

        Assert.True(state.GetProperty("emitting").GetBoolean());
    }

    [Fact]
    public async Task Reports_telemetry_on_when_the_environment_block_holds_every_variable_at_its_value()
    {
        using var studio = new TelemetrySwitchHost(SettingsWith(Owned));

        var state = await studio.State();

        Assert.True(state.GetProperty("emitting").GetBoolean());
    }

    [Fact]
    public async Task Reports_telemetry_off_for_an_environment_block_written_before_the_repository_variable()
    {
        using var studio = new TelemetrySwitchHost(
            SettingsWith(Owned.Where(variable => variable.Key != RepositoryVariable)));

        var state = await studio.State();

        Assert.False(state.GetProperty("emitting").GetBoolean());
    }

    [Fact]
    public async Task Writes_nothing_until_it_is_asked_to()
    {
        using var studio = new TelemetrySwitchHost("{}");

        var state = await studio.State();

        Assert.False(state.GetProperty("emitting").GetBoolean());
        Assert.Equal("{}", studio.SettingsText());
    }

    [Fact]
    public async Task Says_a_session_already_running_will_not_pick_the_change_up()
    {
        using var studio = new TelemetrySwitchHost("{}");

        var note = (await studio.State()).GetProperty("restartNote").GetString();

        Assert.Contains("restart", note!, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Points_the_settings_at_the_collector_address_it_was_configured_with()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);

        Assert.Equal(TelemetrySwitchHost.Collector, studio.Variable("OTEL_EXPORTER_OTLP_ENDPOINT"));
        Assert.Equal(
            TelemetrySwitchHost.Collector,
            (await studio.State()).GetProperty("collectorEndpoint").GetString());
    }

    [Fact]
    public async Task Writes_the_variables_that_make_the_skill_name_arrive_unredacted()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);

        Assert.Equal("1", studio.Variable("CLAUDE_CODE_ENABLE_TELEMETRY"));
        Assert.Equal("otlp", studio.Variable("OTEL_LOGS_EXPORTER"));
        Assert.Equal("1", studio.Variable("OTEL_LOG_TOOL_DETAILS"));
        Assert.Equal("http/protobuf", studio.Variable("OTEL_EXPORTER_OTLP_PROTOCOL"));
    }

    [Fact]
    public async Task Writes_the_variable_that_puts_a_repository_on_every_event()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);

        Assert.Equal("true", studio.Variable(RepositoryVariable));
    }

    [Fact]
    public async Task Creates_a_settings_file_when_the_developer_has_none()
    {
        using var studio = new TelemetrySwitchHost();

        await studio.Turn(emitting: true);

        Assert.True(studio.SettingsExist());
        Assert.Equal("otlp", studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    [Fact]
    public async Task Leaves_the_model_theme_and_status_line_alone_when_turning_on()
    {
        using var studio = new TelemetrySwitchHost(
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
        using var studio = new TelemetrySwitchHost("""{ "env": { "PAGER": "less" } }""");

        await studio.Turn(emitting: true);

        Assert.Equal("less", studio.Variable("PAGER"));
    }

    [Fact]
    public async Task Refuses_to_write_over_settings_it_cannot_parse()
    {
        const string broken = """{ "model": "opus", """;
        using var studio = new TelemetrySwitchHost(broken);

        using var response = await studio.Flip(emitting: true);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(broken, studio.SettingsText());
        Assert.False((await studio.State()).GetProperty("readable").GetBoolean());
    }

    [Fact]
    public async Task Refuses_to_write_over_settings_whose_root_is_not_an_object()
    {
        const string list = """["not", "a", "settings", "document"]""";
        using var studio = new TelemetrySwitchHost(list);

        using var response = await studio.Flip(emitting: true);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(list, studio.SettingsText());
    }

    [Fact]
    public async Task Refuses_to_write_when_the_environment_block_is_not_an_object()
    {
        const string odd = """{ "env": "everything" }""";
        using var studio = new TelemetrySwitchHost(odd);

        using var response = await studio.Flip(emitting: true);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(odd, studio.SettingsText());
        Assert.False((await studio.State()).GetProperty("readable").GetBoolean());
    }

    [Fact]
    public async Task Turning_off_removes_only_the_variables_it_added()
    {
        using var studio = new TelemetrySwitchHost("""{ "model": "opus", "env": { "PAGER": "less" } }""");

        await studio.Turn(emitting: true);
        var state = await studio.Turn(emitting: false);

        Assert.False(state.GetProperty("emitting").GetBoolean());
        Assert.All(Owned.Keys, name => Assert.Null(studio.Variable(name)));
        Assert.Equal("less", studio.Variable("PAGER"));
        Assert.Equal("opus", studio.Settings().GetProperty("model").GetString());
    }

    [Fact]
    public async Task Turning_on_again_brings_an_environment_block_from_before_the_repository_variable_up_to_date()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);
        studio.EditEnvironment(environment => environment.Remove(RepositoryVariable));
        var state = await studio.Turn(emitting: true);

        Assert.True(state.GetProperty("emitting").GetBoolean());
        Assert.Equal("true", studio.Variable(RepositoryVariable));
    }

    [Fact]
    public async Task Turning_off_an_environment_block_brought_up_to_date_leaves_no_repository_variable_behind()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);
        studio.EditEnvironment(environment => environment.Remove(RepositoryVariable));
        await studio.Turn(emitting: true);
        var written = studio.Variable(RepositoryVariable);
        await studio.Turn(emitting: false);

        Assert.Equal("true", written);
        Assert.All(Owned.Keys, name => Assert.Null(studio.Variable(name)));
    }

    [Fact]
    public async Task Turning_off_puts_back_a_value_it_displaced()
    {
        using var studio = new TelemetrySwitchHost(
            """{ "env": { "OTEL_LOGS_EXPORTER": "console", "OTEL_EXPORTER_OTLP_ENDPOINT": "http://elsewhere:4318" } }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.Equal("console", studio.Variable("OTEL_LOGS_EXPORTER"));
        Assert.Equal("http://elsewhere:4318", studio.Variable("OTEL_EXPORTER_OTLP_ENDPOINT"));
    }

    [Fact]
    public async Task Turning_off_keeps_a_variable_the_developer_had_already_set_the_same_way()
    {
        using var studio = new TelemetrySwitchHost(
            """{ "env": { "CLAUDE_CODE_ENABLE_TELEMETRY": "1" } }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.Equal("1", studio.Variable("CLAUDE_CODE_ENABLE_TELEMETRY"));
        Assert.Null(studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    [Fact]
    public async Task Turning_off_leaves_a_variable_the_developer_has_since_changed()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);
        studio.EditEnvironment(environment => environment["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://mine:4318");
        await studio.Turn(emitting: false);

        Assert.Equal("http://mine:4318", studio.Variable("OTEL_EXPORTER_OTLP_ENDPOINT"));
        Assert.Null(studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    [Fact]
    public async Task Turning_off_takes_away_an_environment_block_it_created_itself()
    {
        using var studio = new TelemetrySwitchHost("""{ "model": "opus" }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.False(studio.Settings().TryGetProperty("env", out _));
    }

    [Fact]
    public async Task Turning_off_keeps_an_environment_block_the_developer_already_had()
    {
        using var studio = new TelemetrySwitchHost("""{ "env": {} }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.True(studio.Settings().TryGetProperty("env", out _));
    }

    [Fact]
    public async Task Turning_off_when_there_is_no_settings_file_writes_nothing()
    {
        using var studio = new TelemetrySwitchHost();

        await studio.Turn(emitting: false);

        Assert.False(studio.SettingsExist());
    }

    [Fact]
    public async Task Turning_on_twice_leaves_the_same_settings_as_turning_on_once()
    {
        using var studio = new TelemetrySwitchHost("""{ "env": { "OTEL_LOGS_EXPORTER": "console" } }""");

        await studio.Turn(emitting: true);
        var once = studio.SettingsText();
        await studio.Turn(emitting: true);

        Assert.Equal(once, studio.SettingsText());

        // The displaced value has to survive the second write, or the undo is lost.
        await studio.Turn(emitting: false);
        Assert.Equal("console", studio.Variable("OTEL_LOGS_EXPORTER"));
    }

    private static string SettingsWith(IEnumerable<KeyValuePair<string, string>> variables)
    {
        var environment = new JsonObject();

        foreach (var (name, value) in variables)
        {
            environment[name] = value;
        }

        return new JsonObject { ["env"] = environment }.ToJsonString();
    }
}

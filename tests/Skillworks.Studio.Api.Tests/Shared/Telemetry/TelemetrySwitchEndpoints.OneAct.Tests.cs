using System.Net;

namespace Skillworks.Studio.Api.Tests.Shared.Telemetry;

public sealed partial class TelemetrySwitchEndpointsTests
{
    private static readonly string[] ForASession =
    [
        "OTEL_LOG_USER_PROMPTS",
        "OTEL_LOG_ASSISTANT_RESPONSES",
        "OTEL_LOG_TOOL_CONTENT",
        "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA",
        "OTEL_TRACES_EXPORTER",
    ];

    [Fact]
    public async Task Writes_the_settings_that_keep_the_words_of_a_session()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);

        Assert.Equal("1", studio.Variable("OTEL_LOG_USER_PROMPTS"));
        Assert.Equal("1", studio.Variable("OTEL_LOG_ASSISTANT_RESPONSES"));
        Assert.Equal("1", studio.Variable("OTEL_LOG_TOOL_CONTENT"));
    }

    [Fact]
    public async Task Writes_the_settings_that_make_claude_code_send_spans()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);

        Assert.Equal("1", studio.Variable("CLAUDE_CODE_ENHANCED_TELEMETRY_BETA"));
        Assert.Equal("otlp", studio.Variable("OTEL_TRACES_EXPORTER"));
    }

    [Fact]
    public async Task Writes_every_setting_it_owns_when_it_is_thrown()
    {
        using var studio = new TelemetrySwitchHost("{}");

        await studio.Turn(emitting: true);

        Assert.All(Owned, variable => Assert.Equal(variable.Value, studio.Variable(variable.Key)));
    }

    [Theory]
    [MemberData(nameof(EachForASession))]
    public async Task Reads_as_off_while_any_one_setting_a_session_needs_is_missing(string missing)
    {
        using var studio = new TelemetrySwitchHost(SettingsWith(Owned.Where(variable => variable.Key != missing)));

        var state = await studio.State();

        // All of them or none: a run recorded with all but one of these cannot be read in full either.
        Assert.False(state.GetProperty("emitting").GetBoolean());
    }

    [Fact]
    public async Task Writes_none_of_them_when_the_settings_file_cannot_be_replaced()
    {
        const string before = """{ "model": "opus", "env": { "PAGER": "less" } }""";
        using var studio = new TelemetrySwitchHost(before);
        studio.Seal();

        using var response = await studio.Flip(emitting: true);

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(before, studio.SettingsText());
        Assert.All(Owned.Keys, name => Assert.Null(studio.Variable(name)));
    }

    [Fact]
    public async Task Keeps_no_record_of_displacing_anything_when_the_write_was_refused()
    {
        using var studio = new TelemetrySwitchHost("""{ "model": "opus" }""");
        studio.Seal();

        using (var refused = await studio.Flip(emitting: true))
        {
            Assert.Equal(HttpStatusCode.Conflict, refused.StatusCode);
        }

        // The developer writes the env block the refused act would have claimed as Studio's own.
        studio.Unseal();
        studio.WriteSettings("""{ "model": "opus", "env": {} }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.True(studio.Settings().TryGetProperty("env", out _));
    }

    [Fact]
    public async Task Leaves_settings_it_does_not_own_alone_while_writing_them_all()
    {
        using var studio = new TelemetrySwitchHost(
            """
            {
              "model": "opus",
              "env": { "PAGER": "less", "OTEL_SERVICE_NAME": "mine" }
            }
            """);

        await studio.Turn(emitting: true);

        Assert.All(Owned, variable => Assert.Equal(variable.Value, studio.Variable(variable.Key)));
        Assert.Equal("less", studio.Variable("PAGER"));
        Assert.Equal("mine", studio.Variable("OTEL_SERVICE_NAME"));
        Assert.Equal("opus", studio.Settings().GetProperty("model").GetString());
    }

    [Fact]
    public async Task Turning_off_takes_every_setting_it_owns_away_again()
    {
        using var studio = new TelemetrySwitchHost("""{ "env": { "PAGER": "less" } }""");

        await studio.Turn(emitting: true);
        await studio.Turn(emitting: false);

        Assert.All(Owned.Keys, name => Assert.Null(studio.Variable(name)));
        Assert.Equal("less", studio.Variable("PAGER"));
    }

    public static TheoryData<string> EachForASession() => [.. ForASession];
}

using System.Globalization;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Registration;
using Skillworks.Core.Tests.Harness;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Tests.TraceStore;

public sealed partial class TraceStoreReaderTests
{
    private const string Interaction = "claude_code.interaction";

    private const string Title = "7a000000000000000000000000000001";

    private const string Prompt = "7a000000000000000000000000000002";

    // A whole week, the longest period a store that keeps the ordinary limit will answer for.
    private static readonly DateTimeOffset From = Moment(At(DaysBack(6), "00:00:00"));

    private static readonly DateTimeOffset Until = Moment(At(Tomorrow, "00:00:00"));

    // Longer than a store that keeps the ordinary limit will answer for in one read.
    private static readonly DateTimeOffset MonthBack = Moment(At(DaysBack(29), "00:00:00"));

    [Fact]
    public async Task Reads_back_every_span_of_the_session_it_was_asked_for_oldest_first()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfSessionAsync(session, From, Until, CancellationToken.None);

        // Assert
        Assert.Null(read.Unreachable);
        Assert.Equal(
            [Interaction, "claude_code.llm_request", "claude_code.tool", "claude_code.tool.execution"],
            read.Spans.Select(span => span.Name));
    }

    [Fact]
    public async Task Gathers_a_session_that_ran_as_more_than_one_trace()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());
        await Push(tenant, session, Title, [new RecordedSpan(Interaction, At(Yesterday, "10:01:00"), At(Yesterday, "10:01:02"), "b100000000000001")]);

        // Act
        var read = await Reader(tenant).OfSessionAsync(session, From, Until, CancellationToken.None);

        // Assert
        // Claude Code writes a session's title in a trace of its own, so one trace is never the whole Session.
        Assert.Equal(5, read.Spans.Count);
        Assert.Equal(2, read.Spans.Select(span => span.TraceId).Distinct().Count());
    }

    [Fact]
    public async Task Leaves_out_a_span_that_belongs_to_another_session()
    {
        // Arrange
        var tenant = Tenant();
        var asked = Session();

        await Push(tenant, asked, Prompt, WholeRun());
        await Push(tenant, Session(), Title, [new RecordedSpan(Interaction, At(Yesterday, "11:00:00"), At(Yesterday, "11:00:05"), "c100000000000001")]);

        // Act
        var read = await Reader(tenant).OfSessionAsync(asked, From, Until, CancellationToken.None);

        // Assert
        Assert.All(read.Spans, span => Assert.Equal(asked, span.Attributes["session.id"]));
    }

    [Fact]
    public async Task Carries_what_a_span_says_and_an_event_cannot()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfSessionAsync(session, From, Until, CancellationToken.None);

        // Assert
        var tool = read.Spans.Single(span => span.Name == "claude_code.tool");

        // Which agent ran the Step, what it ran inside, and how long it took are all on the span alone.
        Assert.Equal("agent-a", tool.Attributes["agent_id"]);
        Assert.Equal("toolu_01", tool.Attributes["tool_use_id"]);
        Assert.Equal(Moment(At(Yesterday, "10:00:05")), tool.Started);
        Assert.Equal(Moment(At(Yesterday, "10:00:12")), tool.Ended);
        Assert.Equal(read.Spans.Single(span => span.Name == Interaction).SpanId, tool.ParentSpanId);
    }

    [Fact]
    public async Task Hands_back_the_very_ids_that_were_pushed()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfSessionAsync(session, From, Until, CancellationToken.None);

        // Assert
        var tool = read.Spans.Single(span => span.Name == "claude_code.tool");

        // The next ticket joins an event to its span on these, so an id that comes back reshaped joins nothing.
        Assert.Equal(Prompt, tool.TraceId);
        Assert.Equal("a100000000000003", tool.SpanId);
        Assert.Equal("a100000000000001", tool.ParentSpanId);
    }

    [Fact]
    public async Task Reaches_no_further_back_than_the_first_day_it_was_asked_for()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfSessionAsync(
            session,
            Moment(At(Today, "00:00:00")),
            Until,
            CancellationToken.None);

        // Assert
        Assert.Null(read.Unreachable);
        Assert.Empty(read.Spans);
    }

    [Fact]
    public async Task Reaches_no_further_forward_than_the_last_day_it_was_asked_for()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfSessionAsync(
            session,
            From,
            Moment(At(Today, "00:00:00")),
            CancellationToken.None);

        // Assert
        // The spans' own times fall inside this period, so only the day the store took them in leaves them out.
        Assert.Null(read.Unreachable);
        Assert.Empty(read.Spans);
    }

    [Fact]
    public async Task Reads_back_a_session_over_a_period_longer_than_the_store_will_answer_for()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfSessionAsync(session, MonthBack, Until, CancellationToken.None);

        // Assert
        Assert.Null(read.Unreachable);
        Assert.Equal(4, read.Spans.Count);
    }

    [Fact]
    public async Task Says_a_session_was_cut_short_when_it_holds_more_traces_than_one_read_takes()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());
        await Push(tenant, session, Title, [new RecordedSpan(Interaction, At(Yesterday, "10:01:00"), At(Yesterday, "10:01:02"), "b100000000000001")]);

        // Act
        var read = await Reader(tenant, mostTraces: 1).OfSessionAsync(session, From, Until, CancellationToken.None);

        // Assert
        // What came back stands, or a run the store cut in half would read as one that was never traced.
        Assert.True(read.Shortened);
        Assert.NotEmpty(read.Spans);
        Assert.Null(read.Unreachable);
    }

    [Fact]
    public async Task Says_a_session_was_not_cut_short_when_every_trace_of_it_came_back()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfSessionAsync(session, From, Until, CancellationToken.None);

        // Assert
        Assert.False(read.Shortened);
        Assert.Equal(4, read.Spans.Count);
    }

    [Fact]
    public async Task Says_a_period_was_cut_short_when_it_holds_more_sessions_than_one_read_takes()
    {
        // Arrange
        var tenant = Tenant();

        await Push(tenant, Session(), Prompt, WholeRun());
        await Push(tenant, Session(), Title, [new RecordedSpan(Interaction, At(Yesterday, "11:00:00"), At(Yesterday, "11:00:05"), "c100000000000001")]);

        // Act
        var read = await Reader(tenant, mostSessions: 1).OfPeriodAsync(From, Until, CancellationToken.None);

        // Assert
        Assert.True(read.Shortened);
        Assert.Single(read.Sessions);
        Assert.Null(read.Unreachable);
    }

    [Fact]
    public async Task Says_a_period_was_not_cut_short_when_every_session_in_it_came_back()
    {
        // Arrange
        var tenant = Tenant();

        await Push(tenant, Session(), Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfPeriodAsync(From, Until, CancellationToken.None);

        // Assert
        Assert.False(read.Shortened);
        Assert.Single(read.Sessions);
    }

    [Fact]
    public async Task Names_every_session_the_store_holds_spans_for()
    {
        // Arrange
        var tenant = Tenant();
        var traced = Session();
        var another = Session();

        await Push(tenant, traced, Prompt, WholeRun());
        await Push(tenant, another, Title, [new RecordedSpan(Interaction, At(Yesterday, "11:00:00"), At(Yesterday, "11:00:05"), "c100000000000001")]);

        // Act
        var read = await Reader(tenant).OfPeriodAsync(From, Until, CancellationToken.None);

        // Assert
        Assert.Null(read.Unreachable);
        Assert.Equal(
            new[] { traced, another }.Order(StringComparer.Ordinal),
            read.Sessions.Order(StringComparer.Ordinal));
    }

    [Fact]
    public async Task Names_no_session_traced_after_the_last_day_it_was_asked_for()
    {
        // Arrange
        var tenant = Tenant();

        await Push(tenant, Session(), Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfPeriodAsync(From, Moment(At(Today, "00:00:00")), CancellationToken.None);

        // Assert
        // The spans' own times fall inside this period, so only the day the store took them in leaves them out.
        Assert.Null(read.Unreachable);
        Assert.Empty(read.Sessions);
    }

    [Fact]
    public async Task Names_a_session_over_a_period_longer_than_the_store_will_answer_for()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfPeriodAsync(MonthBack, Until, CancellationToken.None);

        // Assert
        Assert.Null(read.Unreachable);
        Assert.Equal([session], read.Sessions);
    }

    [Fact]
    public async Task Names_no_session_when_the_store_holds_no_spans()
    {
        // Act
        var read = await Reader(Tenant()).OfPeriodAsync(From, Until, CancellationToken.None);

        // Assert
        Assert.Null(read.Unreachable);
        Assert.Empty(read.Sessions);
    }

    [Fact]
    public async Task Names_the_trace_store_and_nothing_else_when_the_sessions_it_holds_cannot_be_read()
    {
        // Arrange
        var down = "http://127.0.0.1:1";

        // Act
        var read = await Reader(Tenant(), down).OfPeriodAsync(From, Until, CancellationToken.None);

        // Assert
        Assert.Empty(read.Sessions);
        Assert.Contains(down, read.Unreachable ?? "");
        Assert.DoesNotContain("events", read.Unreachable ?? "", StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Names_the_trace_store_and_nothing_else_when_it_cannot_be_read()
    {
        // Arrange
        var down = "http://127.0.0.1:1";

        // Act
        var read = await Reader(Tenant(), down).OfSessionAsync(Session(), From, Until, CancellationToken.None);

        // Assert
        // The two stores fall short apart from each other, so this reason never speaks for the events store.
        Assert.Empty(read.Spans);
        Assert.Contains(down, read.Unreachable ?? "");
        Assert.DoesNotContain("events", read.Unreachable ?? "", StringComparison.OrdinalIgnoreCase);
    }

    private static RecordedSpan[] WholeRun() =>
    [
        new(Interaction, At(Yesterday, "10:00:00"), At(Yesterday, "10:00:30"), "a100000000000001"),
        new("claude_code.llm_request", At(Yesterday, "10:00:01"), At(Yesterday, "10:00:04"), "a100000000000002", "a100000000000001"),
        new("claude_code.tool", At(Yesterday, "10:00:05"), At(Yesterday, "10:00:12"), "a100000000000003", "a100000000000001", "agent-a", "toolu_01"),
        new("claude_code.tool.execution", At(Yesterday, "10:00:06"), At(Yesterday, "10:00:11"), "a100000000000004", "a100000000000003", "agent-a"),
    ];

    private static Task Push(string tenant, string session, string trace, IReadOnlyList<RecordedSpan> spans) =>
        TestTempo.PushAsync(tenant, session, [.. spans.Select(span => span.Record(trace, session))]);

    // The real registration, so the address and the timeout under test are the ones Studio runs with.
    private static TraceStoreReader Reader(
        string tenant,
        string? address = null,
        int? mostTraces = null,
        int? mostSessions = null,
        int? sessionTimeoutSeconds = null,
        HttpMessageHandler? store = null)
    {
        var settings = new Dictionary<string, string?>
        {
            ["Tempo:Address"] = address ?? TestTempo.Address.ToString(),
            ["Tempo:Tenant"] = tenant,
        };

        // Left out unless asked for, as an empty value binds as none and would hide the default.
        if (mostTraces is { } traces)
        {
            settings["Tempo:MostTraces"] = traces.ToString(CultureInfo.InvariantCulture);
        }

        if (mostSessions is { } runs)
        {
            settings["Tempo:MostSessions"] = runs.ToString(CultureInfo.InvariantCulture);
        }

        if (sessionTimeoutSeconds is { } seconds)
        {
            settings["Tempo:SessionTimeoutSeconds"] = seconds.ToString(CultureInfo.InvariantCulture);
        }

        var services = new ServiceCollection()
            .AddSkillworksCore(new ConfigurationBuilder().AddInMemoryCollection(settings).Build());

        // Only the handler is replaced, and after the registration that clears them, so Studio's own timeout stays under test.
        if (store is not null)
        {
            services.AddHttpClient(TraceStoreReader.ClientName).ConfigurePrimaryHttpMessageHandler(() => store);
        }

        return services.BuildServiceProvider().GetRequiredService<TraceStoreReader>();
    }

    // Its own tenant, so no other test's spans reach this one's answers.
    private static string Tenant() => Guid.NewGuid().ToString("N");

    private static string Session() => Guid.NewGuid().ToString();

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);
}

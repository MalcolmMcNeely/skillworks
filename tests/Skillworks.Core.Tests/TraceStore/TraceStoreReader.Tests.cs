using System.Globalization;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Registration;
using Skillworks.Core.Tests.Harness;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Tests.TraceStore;

public sealed class TraceStoreReaderTests
{
    private const string Interaction = "claude_code.interaction";

    private const string Title = "7a000000000000000000000000000001";

    private const string Prompt = "7a000000000000000000000000000002";

    private static readonly DateTimeOffset From = Moment("2026-09-08T00:00:00Z");

    [Fact]
    public async Task Reads_back_every_span_of_the_session_it_was_asked_for_oldest_first()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await Push(tenant, session, Prompt, WholeRun());

        // Act
        var read = await Reader(tenant).OfSessionAsync(session, From, CancellationToken.None);

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
        await Push(tenant, session, Title, [new RecordedSpan(Interaction, "2026-09-14T10:01:00Z", "2026-09-14T10:01:02Z", "b100000000000001")]);

        // Act
        var read = await Reader(tenant).OfSessionAsync(session, From, CancellationToken.None);

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
        await Push(tenant, Session(), Title, [new RecordedSpan(Interaction, "2026-09-14T11:00:00Z", "2026-09-14T11:00:05Z", "c100000000000001")]);

        // Act
        var read = await Reader(tenant).OfSessionAsync(asked, From, CancellationToken.None);

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
        var read = await Reader(tenant).OfSessionAsync(session, From, CancellationToken.None);

        // Assert
        var tool = read.Spans.Single(span => span.Name == "claude_code.tool");

        // Which agent ran the Step, what it ran inside, and how long it took are all on the span alone.
        Assert.Equal("agent-a", tool.Attributes["agent_id"]);
        Assert.Equal("toolu_01", tool.Attributes["tool_use_id"]);
        Assert.Equal(Moment("2026-09-14T10:00:05Z"), tool.Started);
        Assert.Equal(Moment("2026-09-14T10:00:12Z"), tool.Ended);
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
        var read = await Reader(tenant).OfSessionAsync(session, From, CancellationToken.None);

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
        var read = await Reader(tenant).OfSessionAsync(session, Moment("2026-09-15T00:00:00Z"), CancellationToken.None);

        // Assert
        Assert.Null(read.Unreachable);
        Assert.Empty(read.Spans);
    }

    [Fact]
    public async Task Names_every_session_the_store_holds_spans_for()
    {
        // Arrange
        var tenant = Tenant();
        var traced = Session();
        var another = Session();

        await Push(tenant, traced, Prompt, WholeRun());
        await Push(tenant, another, Title, [new RecordedSpan(Interaction, "2026-09-14T11:00:00Z", "2026-09-14T11:00:05Z", "c100000000000001")]);

        // Act
        var read = await Reader(tenant).OfPeriodAsync(From, CancellationToken.None);

        // Assert
        Assert.Null(read.Unreachable);
        Assert.Equal(
            new[] { traced, another }.Order(StringComparer.Ordinal),
            read.Sessions.Order(StringComparer.Ordinal));
    }

    [Fact]
    public async Task Names_no_session_when_the_store_holds_no_spans()
    {
        // Act
        var read = await Reader(Tenant()).OfPeriodAsync(From, CancellationToken.None);

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
        var read = await Reader(Tenant(), down).OfPeriodAsync(From, CancellationToken.None);

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
        var read = await Reader(Tenant(), down).OfSessionAsync(Session(), From, CancellationToken.None);

        // Assert
        // The two stores fall short apart from each other, so this reason never speaks for the events store.
        Assert.Empty(read.Spans);
        Assert.Contains(down, read.Unreachable ?? "");
        Assert.DoesNotContain("events", read.Unreachable ?? "", StringComparison.OrdinalIgnoreCase);
    }

    private static RecordedSpan[] WholeRun() =>
    [
        new(Interaction, "2026-09-14T10:00:00Z", "2026-09-14T10:00:30Z", "a100000000000001"),
        new("claude_code.llm_request", "2026-09-14T10:00:01Z", "2026-09-14T10:00:04Z", "a100000000000002", "a100000000000001"),
        new("claude_code.tool", "2026-09-14T10:00:05Z", "2026-09-14T10:00:12Z", "a100000000000003", "a100000000000001", "agent-a", "toolu_01"),
        new("claude_code.tool.execution", "2026-09-14T10:00:06Z", "2026-09-14T10:00:11Z", "a100000000000004", "a100000000000003", "agent-a"),
    ];

    private static Task Push(string tenant, string session, string trace, IReadOnlyList<RecordedSpan> spans) =>
        TestTempo.PushAsync(tenant, session, [.. spans.Select(span => span.Record(trace, session))]);

    // The real registration, so the address and the timeout under test are the ones Studio runs with.
    private static TraceStoreReader Reader(string tenant, string? address = null) =>
        new ServiceCollection()
            .AddSkillworksCore(new ConfigurationBuilder()
                .AddInMemoryCollection(new Dictionary<string, string?>
                {
                    ["Tempo:Address"] = address ?? TestTempo.Address.ToString(),
                    ["Tempo:Tenant"] = tenant,
                })
                .Build())
            .BuildServiceProvider()
            .GetRequiredService<TraceStoreReader>();

    // Its own tenant, so no other test's spans reach this one's answers.
    private static string Tenant() => Guid.NewGuid().ToString("N");

    private static string Session() => Guid.NewGuid().ToString();

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);
}

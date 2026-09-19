using Skillworks.Core.Shared.Stores.TraceStore;
using Skillworks.Core.Tests.Shared.Harness.StandIns;

namespace Skillworks.Core.Tests.Shared.Stores.TraceStore;

public sealed partial class TraceStoreReaderTests
{
    // Long enough that a handful of requests outlast the budget, and well inside the timeout one request gets.
    private static readonly TimeSpan Slowly = TimeSpan.FromMilliseconds(800);

    private const int BudgetSeconds = 3;

    private const int TraceDigits = 32;

    private const int SpanDigits = 16;

    [Fact]
    public async Task Falls_short_as_a_whole_when_a_slow_store_holds_more_traces_than_the_budget_covers()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await PushTraces(tenant, session, 4);

        using var slow = new SlowTraceStore(Slowly);

        // Act
        var read = await SlowReader(tenant, slow).OfSessionAsync(session, From, Until, CancellationToken.None);

        // Assert
        // Every request on its own fits the budget, so only a budget over the whole read can run out here.
        Assert.NotNull(read.Unreachable);
        Assert.Empty(read.Spans);
    }

    [Fact]
    public async Task Reads_a_session_whole_from_a_slow_store_when_its_traces_fit_the_budget()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await PushTraces(tenant, session, 1);

        using var slow = new SlowTraceStore(Slowly);

        // Act
        var read = await SlowReader(tenant, slow).OfSessionAsync(session, From, Until, CancellationToken.None);

        // Assert
        // The same wait as the read that fell short, so a budget too short for one request would fail this too.
        Assert.Null(read.Unreachable);
        Assert.Single(read.Spans);
    }

    // The timeout one request gets is left at its default, so only the whole-read budget can end these reads.
    private static TraceStoreReader SlowReader(string tenant, SlowTraceStore slow) =>
        Reader(tenant, sessionTimeoutSeconds: BudgetSeconds, store: slow);

    // A trace of its own for each, as the store is asked for a session's traces one request at a time.
    private static async Task PushTraces(string tenant, string session, int traces)
    {
        for (var at = 1; at <= traces; at++)
        {
            await Push(
                tenant,
                session,
                Numbered(at, TraceDigits),
                [new RecordedSpan(Interaction, At(Yesterday, "10:00:00"), At(Yesterday, "10:00:30"), Numbered(at, SpanDigits))]);
        }
    }

    // Trailing zeroes, because a store hands an identifier back with its leading ones stripped.
    private static string Numbered(int at, int digits) => $"7{at}".PadRight(digits, '0');
}

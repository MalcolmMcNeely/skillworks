using Skillworks.Core.Shared.Stores.TraceStore;
using Skillworks.Core.Tests.Shared.Harness;
using Skillworks.Core.Tests.Shared.Harness.StandIns;

namespace Skillworks.Core.Tests.Shared.Stores.TraceStore;

public sealed partial class TraceStoreReaderTests
{
    private const int BudgetSeconds = 3;

    // Trailing zeroes, because a store hands an identifier back with its leading ones stripped.
    private const string HeldTrace = "71000000000000000000000000000000";

    private const string HeldSpan = "7100000000000000";

    [Fact]
    public async Task Falls_short_as_a_whole_when_the_budget_runs_out_while_a_read_is_still_out()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await PushOneTrace(tenant, session);

        using var stalling = new StallingTraceStore();
        var clock = HarnessClock.Still();

        // Act
        var reading = HeldReader(tenant, stalling, clock).OfSessionAsync(session, From, Until, CancellationToken.None);

        await stalling.Asked;

        clock.Advance(TimeSpan.FromSeconds(BudgetSeconds + 1));

        var read = await reading;

        // Assert
        // The budget is the one wait built on the Clock, so moving it can end this read and nothing else can.
        Assert.NotNull(read.Unreachable);
        Assert.Empty(read.Spans);
    }

    [Fact]
    public async Task Reads_a_session_whole_when_the_store_answers_inside_the_budget()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await PushOneTrace(tenant, session);

        using var stalling = new StallingTraceStore();
        var clock = HarnessClock.Still();

        // Act
        var reading = HeldReader(tenant, stalling, clock).OfSessionAsync(session, From, Until, CancellationToken.None);

        await stalling.Asked;

        stalling.LetGo();

        var read = await reading;

        // Assert
        // The same budget as the read that fell short, so only moving the Clock tells the two apart.
        Assert.Null(read.Unreachable);
        Assert.Single(read.Spans);
    }

    // The timeout one request gets is left at its default, so only the whole-read budget can end these reads.
    private static TraceStoreReader HeldReader(string tenant, StallingTraceStore stalling, TimeProvider clock) =>
        Reader(tenant, sessionTimeoutSeconds: BudgetSeconds, store: stalling, clock: clock);

    private static Task PushOneTrace(string tenant, string session) =>
        Push(
            tenant,
            session,
            HeldTrace,
            [new RecordedSpan(Interaction, At(Yesterday, "10:00:00"), At(Yesterday, "10:00:30"), HeldSpan)]);
}

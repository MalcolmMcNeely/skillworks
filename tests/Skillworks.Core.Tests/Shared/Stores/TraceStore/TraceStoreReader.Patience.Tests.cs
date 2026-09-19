using Skillworks.Core.Shared.Stores.TraceStore;
using Skillworks.Core.Tests.Shared.Harness;
using Skillworks.Core.Tests.Shared.Harness.StandIns;

namespace Skillworks.Core.Tests.Shared.Stores.TraceStore;

public sealed partial class TraceStoreReaderTests
{
    // Longer than any run, so a Patience measured on the machine's clock could never be spent inside these tests.
    private const int PatienceSeconds = 300;

    private const int BeyondReach = PatienceSeconds * 2;

    // Trailing zeroes, because a store hands an identifier back with its leading ones stripped.
    private const string HeldTrace = "71000000000000000000000000000000";

    private const string HeldSpan = "7100000000000000";

    [Fact]
    public async Task Reports_a_Gap_when_one_request_outlasts_the_Patience_it_is_given()
    {
        // Arrange
        using var stalling = new StallingTraceStore();
        var clock = HarnessClock.Still();
        var reader = Reader(Tenant(), requestPatienceSeconds: PatienceSeconds, store: stalling, clock: clock);

        // Act
        // A period has no Patience over it as a whole, so a request's own is the only wait that can end this read.
        var reading = reader.OfPeriodAsync(From, Until, CancellationToken.None);

        await stalling.Asked;

        clock.Advance(TimeSpan.FromSeconds(PatienceSeconds + 1));

        var read = await reading;

        // Assert
        Assert.Equal(
            $"{TestTempo.Address} did not answer inside the {PatienceSeconds} seconds Studio waits for one request",
            read.Unreachable);
        Assert.Empty(read.Sessions);
    }

    [Fact]
    public async Task Reports_a_Gap_when_one_request_of_a_session_outlasts_its_own_Patience()
    {
        // Arrange
        var tenant = Tenant();
        var session = Session();

        await PushOneTrace(tenant, session);

        using var stalling = new StallingTraceStore();
        var clock = HarnessClock.Still();

        // The way round Studio runs: a request gives up long before the session it belongs to does.
        var reader = Reader(
            tenant,
            requestPatienceSeconds: PatienceSeconds,
            sessionPatienceSeconds: BeyondReach,
            store: stalling,
            clock: clock);

        // Act
        var reading = reader.OfSessionAsync(session, From, Until, CancellationToken.None);

        await stalling.Asked;

        clock.Advance(TimeSpan.FromSeconds(PatienceSeconds + 1));

        var read = await reading;

        // Assert
        // Taking this request's Patience off the token it sends inside leaves the session's wait out of reach.
        Assert.Equal(
            $"{TestTempo.Address} did not answer inside the {PatienceSeconds} seconds Studio waits for one request",
            read.Unreachable);
        Assert.Empty(read.Spans);
    }

    [Fact]
    public async Task Reports_a_Gap_when_a_whole_session_outlasts_the_Patience_over_it()
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

        clock.Advance(TimeSpan.FromSeconds(PatienceSeconds + 1));

        var read = await reading;

        // Assert
        Assert.Equal(
            $"{TestTempo.Address} did not answer inside the {PatienceSeconds} seconds Studio waits for a whole session",
            read.Unreachable);
        Assert.Empty(read.Spans);
    }

    [Fact]
    public async Task Reads_a_session_whole_when_the_store_answers_inside_the_Patience_over_it()
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
        // The same setup as the read that fell short, so only moving the Clock tells the two tests apart.
        Assert.Null(read.Unreachable);
        Assert.Single(read.Spans);
    }

    [Fact]
    public async Task Lets_the_caller_go_rather_than_calling_the_store_unreachable()
    {
        // Arrange
        using var stalling = new StallingTraceStore();
        using var leaving = new CancellationTokenSource();
        var clock = HarnessClock.Still();

        // Act
        var reading = HeldReader(Tenant(), stalling, clock)
            .OfSessionAsync(Session(), From, Until, leaving.Token);

        await stalling.Asked;

        await leaving.CancelAsync();

        // Assert
        // A closed browser tab reaches the reader as this, and an outage it never saw would be reported as a Gap.
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => reading);
    }

    // The request's Patience is put beyond the session's, so a read that ends early names the wait the test moved past.
    private static TraceStoreReader HeldReader(string tenant, StallingTraceStore stalling, TimeProvider clock) =>
        Reader(
            tenant,
            requestPatienceSeconds: BeyondReach,
            sessionPatienceSeconds: PatienceSeconds,
            store: stalling,
            clock: clock);

    private static Task PushOneTrace(string tenant, string session) =>
        Push(
            tenant,
            session,
            HeldTrace,
            [new RecordedSpan(Interaction, At(Yesterday, "10:00:00"), At(Yesterday, "10:00:30"), HeldSpan)]);
}

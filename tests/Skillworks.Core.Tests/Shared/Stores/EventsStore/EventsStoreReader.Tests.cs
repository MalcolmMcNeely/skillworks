using System.Globalization;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Shared.Stores;
using Skillworks.Core.Shared.Stores.EventsStore;
using Skillworks.Core.Tests.Shared.Harness;
using Skillworks.Core.Tests.Shared.Harness.StandIns;

namespace Skillworks.Core.Tests.Shared.Stores.EventsStore;

public sealed class EventsStoreReaderTests
{
    // Longer than any run, so a Patience measured on the machine's clock could never be spent inside this test.
    private const int PatienceSeconds = 300;

    // A wider period splits into a request each, so only one day puts a single Patience under test.
    private static readonly EventQuery OneDay = new(
        EventQuery.AnyEvent,
        Moment(At(Yesterday, "00:00:00")),
        Moment(At(Today, "00:00:00")));

    [Fact]
    public async Task Reports_a_Gap_when_a_read_outlasts_the_Patience()
    {
        // Arrange
        using var stalling = new StallingEventsStore();
        var clock = HarnessClock.Still();

        // Act
        var reading = Reader(stalling, clock).CountAsync(OneDay, [], CancellationToken.None);

        await stalling.Asked;

        clock.Advance(TimeSpan.FromSeconds(PatienceSeconds + 1));

        var read = await reading;

        // Assert
        // The reason names the Patience, so a wait ended by anything else would fail here rather than pass slowly.
        Assert.Contains($"inside the {PatienceSeconds} seconds", read.Unreachable ?? "", StringComparison.Ordinal);
        Assert.Empty(read.Groups);
    }

    [Fact]
    public async Task Lets_the_caller_go_rather_than_calling_the_store_unreachable()
    {
        // Arrange
        using var stalling = new StallingEventsStore();
        using var leaving = new CancellationTokenSource();
        var clock = HarnessClock.Still();

        // Act
        var reading = Reader(stalling, clock).CountAsync(OneDay, [], leaving.Token);

        await stalling.Asked;

        await leaving.CancelAsync();

        // Assert
        // A closed browser tab reaches the reader as this, and an outage it never saw would be reported as a Gap.
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => reading);
    }

    // The real registration, so the address and the Patience under test are the ones Studio runs with.
    private static EventsStoreReader Reader(HttpMessageHandler store, TimeProvider clock)
    {
        var settings = new Dictionary<string, string?>
        {
            ["Loki:PatienceSeconds"] = PatienceSeconds.ToString(CultureInfo.InvariantCulture),
        };

        var services = new ServiceCollection();

        // Ahead of AddStores, which falls back to the machine's clock only where nothing has supplied one.
        services.AddSingleton(clock);

        services.AddStores(new ConfigurationBuilder().AddInMemoryCollection(settings).Build());

        // Only the handler is replaced, and after the registration that clears them, so Studio's own Patience stays under test.
        services.AddHttpClient(EventsStoreReader.ClientName).ConfigurePrimaryHttpMessageHandler(() => store);

        return services.BuildServiceProvider().GetRequiredService<EventsStoreReader>();
    }

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);
}

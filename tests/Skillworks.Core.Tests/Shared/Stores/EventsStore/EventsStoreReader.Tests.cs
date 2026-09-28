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
    // Under the ceiling a request's Patience is held to, or the sentence would name seconds nobody asked for.
    private const int PatienceSeconds = 60;

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

    [Fact]
    public async Task Lets_no_more_than_four_reads_out_at_the_store_at_once()
    {
        // Arrange
        using var stalling = new StallingEventsStore();
        var (reader, line) = Watched(stalling, HarnessClock.Still());

        // Act
        var readings = Enumerable.Range(0, 6).Select(_ => reader.CountAsync(OneDay, [], CancellationToken.None)).ToList();

        await stalling.AskedFor(4);
        await line.JoinedBy(6);

        stalling.LetGo();

        await Task.WhenAll(readings);

        // Assert
        Assert.Equal(4, stalling.MostAtOnce);
        Assert.Equal(6, stalling.Queries.Count);
    }

    [Fact]
    public async Task Sends_the_reads_it_holds_first_come_first_served()
    {
        // Arrange
        using var stalling = new StallingEventsStore();
        var (reader, line) = Watched(stalling, HarnessClock.Still(), readsAtOnce: 1);

        var first = reader.CountAsync(Named("first"), [], CancellationToken.None);

        await stalling.Asked;

        var second = reader.CountAsync(Named("second"), [], CancellationToken.None);

        await line.JoinedBy(2);

        var third = reader.CountAsync(Named("third"), [], CancellationToken.None);

        await line.JoinedBy(3);

        // Act
        stalling.LetGo();

        await Task.WhenAll(first, second, third);

        // Assert
        Assert.Collection(
            stalling.Queries,
            query => Assert.Contains("claude_code.first", query, StringComparison.Ordinal),
            query => Assert.Contains("claude_code.second", query, StringComparison.Ordinal),
            query => Assert.Contains("claude_code.third", query, StringComparison.Ordinal));
    }

    [Fact]
    public async Task Starts_the_Patience_when_the_read_leaves_the_line()
    {
        // Arrange
        using var stalling = new StallingEventsStore();
        var clock = HarnessClock.Still();
        var (reader, line) = Watched(stalling, clock, readsAtOnce: 1);

        var first = reader.CountAsync(OneDay, [], CancellationToken.None);

        await stalling.Asked;

        var held = reader.CountAsync(OneDay, [], CancellationToken.None);

        await line.JoinedBy(2);

        // Act
        clock.Advance(TimeSpan.FromSeconds(PatienceSeconds + 1));

        var ranOut = await first;

        await stalling.AskedFor(2);

        stalling.LetGo();

        var read = await held;

        // Assert
        // The read ahead of it ran out, so the Clock did move past a Patience while this one waited its turn.
        Assert.NotNull(ranOut.Unreachable);
        Assert.Null(read.Unreachable);
    }

    [Fact]
    public async Task Never_sends_a_read_whose_caller_left_while_it_waited()
    {
        // Arrange
        using var stalling = new StallingEventsStore();
        using var leaving = new CancellationTokenSource();
        var (reader, line) = Watched(stalling, HarnessClock.Still(), readsAtOnce: 1);

        var first = reader.CountAsync(OneDay, [], CancellationToken.None);

        await stalling.Asked;

        var left = reader.CountAsync(Named("left"), [], leaving.Token);

        await line.JoinedBy(2);

        var after = reader.CountAsync(OneDay, [], CancellationToken.None);

        await line.JoinedBy(3);

        // Act
        await leaving.CancelAsync();

        // A cancel can return before the read leaves the line, and a place freed then can still go to it.
        await Task.WhenAny(left);

        stalling.LetGo();

        await Task.WhenAll(first, after);

        // Assert
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => left);

        // The read behind it goes out only after it would have, so the store has seen every read it ever will.
        Assert.DoesNotContain(stalling.Queries, query => query.Contains("claude_code.left", StringComparison.Ordinal));
        Assert.Equal(2, stalling.Queries.Count);
    }

    [Fact]
    public async Task Reports_each_refused_read_as_a_Gap_without_waiting()
    {
        // Arrange
        using var refusing = new RefusingEventsStore();
        var reader = Reader(refusing, HarnessClock.Still());

        // Act
        // Awaited with the Clock held still, so a refusal that waited out a Patience would never return.
        var reads = await Task.WhenAll(
            Enumerable.Range(0, 5).Select(_ => reader.CountAsync(OneDay, [], CancellationToken.None)));

        // Assert
        Assert.All(reads, read => Assert.Contains("could not be read", read.Unreachable ?? "", StringComparison.Ordinal));
    }

    [Fact]
    public async Task Opens_a_new_connection_for_each_read()
    {
        // Arrange
        using var store = new SocketEventsStore();
        var reader = Reader(store.Address, HarnessClock.Still());

        // Act
        var first = await reader.CountAsync(OneDay, [], CancellationToken.None);
        var second = await reader.CountAsync(OneDay, [], CancellationToken.None);

        // Assert
        Assert.Null(first.Unreachable);
        Assert.Null(second.Unreachable);

        // A container's port forward resets a reused connection, which reads as a Gap.
        Assert.Equal(2, store.Connections);
    }

    // The real registration, so the address, the Patience and the line under test are the ones Studio runs with.
    private static EventsStoreReader Reader(HttpMessageHandler store, TimeProvider clock, int? readsAtOnce = null) =>
        Handled(store, clock, readsAtOnce).BuildServiceProvider().GetRequiredService<EventsStoreReader>();

    // Built from the same settings, so the line under test is still the size and the order Studio runs with.
    private static (EventsStoreReader Reader, HarnessLine Line) Watched(HttpMessageHandler store, TimeProvider clock, int? readsAtOnce = null)
    {
        var services = Handled(store, clock, readsAtOnce);

        services.AddSingleton<HarnessLine>();
        services.AddSingleton<EventsStoreLine>(provider => provider.GetRequiredService<HarnessLine>());

        var provider = services.BuildServiceProvider();

        return (provider.GetRequiredService<EventsStoreReader>(), provider.GetRequiredService<HarnessLine>());
    }

    private static ServiceCollection Handled(HttpMessageHandler store, TimeProvider clock, int? readsAtOnce)
    {
        var services = Registered(clock, readsAtOnce, address: null);

        // Only the handler is replaced, and after the registration that clears them, so Studio's own Patience stays under test.
        services.AddHttpClient(EventsStoreReader.ClientName).ConfigurePrimaryHttpMessageHandler(() => store);

        return services;
    }

    // Studio's own handler too, so the connections a store sees are the ones Studio opens.
    private static EventsStoreReader Reader(Uri address, TimeProvider clock) =>
        Registered(clock, readsAtOnce: null, address).BuildServiceProvider().GetRequiredService<EventsStoreReader>();

    private static ServiceCollection Registered(TimeProvider clock, int? readsAtOnce, Uri? address)
    {
        var settings = new Dictionary<string, string?>
        {
            ["Loki:PatienceSeconds"] = PatienceSeconds.ToString(CultureInfo.InvariantCulture),
        };

        // Left out unless asked for, so the default is the one under test.
        if (readsAtOnce is { } reads)
        {
            settings["Loki:ReadsAtOnce"] = reads.ToString(CultureInfo.InvariantCulture);
        }

        if (address is not null)
        {
            settings["Loki:Address"] = address.ToString();
        }

        var services = new ServiceCollection();

        // Ahead of AddStores, which falls back to the machine's clock only where nothing has supplied one.
        services.AddSingleton(clock);

        services.AddStores(new ConfigurationBuilder().AddInMemoryCollection(settings).Build());

        return services;
    }

    private static EventQuery Named(string eventName) => OneDay with { EventName = eventName };

    private static DateTimeOffset Moment(string at) => DateTimeOffset.Parse(at, CultureInfo.InvariantCulture);
}

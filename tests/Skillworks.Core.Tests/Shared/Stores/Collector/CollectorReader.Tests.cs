using System.Globalization;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Skillworks.Core.Shared.Stores;
using Skillworks.Core.Shared.Stores.Collector;
using Skillworks.Core.Tests.Shared.Harness;
using Skillworks.Core.Tests.Shared.Harness.StandIns;

namespace Skillworks.Core.Tests.Shared.Stores.Collector;

public sealed class CollectorReaderTests
{
    // Under the ceiling a request's Patience is held to, or the sentence would name seconds nobody asked for.
    private const int PatienceSeconds = 60;

    // Two of these outlast one Patience, so a wait shared by both doors would end a read that each door answered inside.
    private const int PartOfIt = PatienceSeconds - 20;

    [Fact]
    public async Task Reports_a_shut_door_when_the_first_knock_outlasts_the_Patience()
    {
        // Arrange
        using var collector = new HeldCollector();
        var clock = HarnessClock.Still();

        // Act
        var knocking = Reader(collector, clock).AnsweringAsync(CancellationToken.None);

        await collector.Knocked(HeldCollector.EventsDoor);

        clock.Advance(TimeSpan.FromSeconds(PatienceSeconds + 1));

        var answer = await knocking;

        // Assert
        Assert.Equal(CollectorState.Shut, answer.State);

        // The reason names the door and the Patience, so a knock ended by anything else would fail here.
        Assert.Equal(Waited("events", "v1/logs"), answer.Detail);
    }

    [Fact]
    public async Task Reports_a_shut_door_when_a_later_knock_outlasts_the_Patience()
    {
        // Arrange
        using var collector = new HeldCollector();
        var clock = HarnessClock.Still();

        collector.LetGo(HeldCollector.EventsDoor);

        // Act
        var knocking = Reader(collector, clock).AnsweringAsync(CancellationToken.None);

        await collector.Knocked(HeldCollector.SpansDoor);

        clock.Advance(TimeSpan.FromSeconds(PatienceSeconds + 1));

        var answer = await knocking;

        // Assert
        // A door reached only after another answered is bounded too, or one open door would let the next hang for ever.
        Assert.Equal(CollectorState.Shut, answer.State);
        Assert.Equal(Waited("Spans", "v1/traces"), answer.Detail);
    }

    [Fact]
    public async Task Gives_each_door_a_Patience_of_its_own()
    {
        // Arrange
        using var collector = new HeldCollector();
        var clock = HarnessClock.Still();

        // Act
        var knocking = Reader(collector, clock).AnsweringAsync(CancellationToken.None);

        await collector.Knocked(HeldCollector.EventsDoor);

        clock.Advance(TimeSpan.FromSeconds(PartOfIt));

        collector.LetGo(HeldCollector.EventsDoor);

        await collector.Knocked(HeldCollector.SpansDoor);

        clock.Advance(TimeSpan.FromSeconds(PartOfIt));

        collector.LetGo(HeldCollector.SpansDoor);

        var answer = await knocking;

        // Assert
        // Both doors answered inside their own Patience while together outlasting one, which one wait for the pair would have spent.
        Assert.Equal(CollectorState.Answering, answer.State);
    }

    [Fact]
    public async Task Lets_the_caller_go_rather_than_calling_a_door_shut()
    {
        // Arrange
        using var collector = new HeldCollector();
        using var leaving = new CancellationTokenSource();
        var clock = HarnessClock.Still();

        // Act
        var knocking = Reader(collector, clock).AnsweringAsync(leaving.Token);

        await collector.Knocked(HeldCollector.EventsDoor);

        await leaving.CancelAsync();

        // Assert
        // A closed browser tab reaches the reader as this, and an outage it never saw would light the Lamp.
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => knocking);
    }

    private static string Waited(string door, string route) =>
        $"The {door} door at {new CollectorOptions().ResolvedAddress()}{route} " +
        $"did not answer inside the {PatienceSeconds} seconds Studio waits for one request.";

    // The real registration, so the address and the Patience under test are the ones Studio runs with.
    private static CollectorReader Reader(HttpMessageHandler collector, TimeProvider clock)
    {
        var settings = new Dictionary<string, string?>
        {
            ["Collector:PatienceSeconds"] = PatienceSeconds.ToString(CultureInfo.InvariantCulture),
        };

        var services = new ServiceCollection();

        // Ahead of AddStores, which falls back to the machine's clock only where nothing has supplied one.
        services.AddSingleton(clock);

        services.AddStores(new ConfigurationBuilder().AddInMemoryCollection(settings).Build());

        // Only the handler is replaced, and after the registration that clears them, so Studio's own Patience stays under test.
        services.AddHttpClient(CollectorReader.ClientName).ConfigurePrimaryHttpMessageHandler(() => collector);

        return services.BuildServiceProvider().GetRequiredService<CollectorReader>();
    }
}
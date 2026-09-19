using System.Text;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.Shared.Stores.Collector;

public sealed class CollectorReader(IHttpClientFactory clients, IOptions<CollectorOptions> options, TimeProvider clock)
{
    public const string ClientName = "collector";

    // An empty payload holds no event and no Span, so a knock stores nothing and moves no figure a reader sees.
    private static readonly Door[] Doors =
    [
        new("events", "v1/logs", """{"resourceLogs":[]}"""),
        new("Spans", "v1/traces", """{"resourceSpans":[]}"""),
    ];

    public async Task<CollectorAnswer> AnsweringAsync(CancellationToken cancellationToken)
    {
        var address = options.Value.ResolvedAddress();

        // The first shut door answers for the part, because a part is one Lamp however many doors it has.
        foreach (var door in Doors)
        {
            if (await KnockAsync(door, address, cancellationToken) is { } shut)
            {
                return CollectorAnswer.Shut(shut);
            }
        }

        return CollectorAnswer.Answering(address);
    }

    private async Task<string?> KnockAsync(Door door, Uri address, CancellationToken cancellationToken)
    {
        var client = clients.CreateClient(ClientName);
        var patience = Patience.PerRequest(options.Value.PatienceSeconds);
        var subject = Subject(door, address);

        using var payload = new StringContent(door.Payload, Encoding.UTF8, "application/json");

        // One per door, so a Collector slow on the first still gets its whole Patience to answer on the second.
        using var spent = new CancellationTokenSource(patience.Length, clock);
        using var within = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, spent.Token);

        try
        {
            using var response = await client.PostAsync(door.Route, payload, within.Token);

            return response.IsSuccessStatusCode
                ? null
                : $"{subject} answered {(int)response.StatusCode}.";
        }
        catch (Exception failure) when (Outside(failure, cancellationToken))
        {
            // A Patience that ran out says so, or a reader is told only that something somewhere was cancelled.
            return spent.IsCancellationRequested
                ? patience.RanOut(subject, Patience.OneRequest)
                : $"{subject} could not be reached ({failure.Message}).";
        }
    }

    private static string Subject(Door door, Uri address) => $"The {door.Name} door at {address}{door.Route}";

    // Caller cancellation must propagate, or a closed browser tab would be reported as an outage.
    private static bool Outside(Exception failure, CancellationToken cancellationToken) =>
        failure is HttpRequestException ||
        (failure is TaskCanceledException && !cancellationToken.IsCancellationRequested);

    private sealed record Door(string Name, string Route, string Payload);
}

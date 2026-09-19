using System.Text;
using Microsoft.Extensions.Options;

namespace Skillworks.Core.Shared.Stores.Collector;

public sealed class CollectorReader(IHttpClientFactory clients, IOptions<CollectorOptions> options)
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

        using var payload = new StringContent(door.Payload, Encoding.UTF8, "application/json");

        try
        {
            using var response = await client.PostAsync(door.Route, payload, cancellationToken);

            return response.IsSuccessStatusCode
                ? null
                : $"The {door.Name} door at {address}{door.Route} answered {(int)response.StatusCode}.";
        }
        catch (Exception failure) when (Outside(failure, cancellationToken))
        {
            return $"The {door.Name} door at {address}{door.Route} could not be reached: {failure.Message}";
        }
    }

    // Caller cancellation must propagate, or a closed browser tab would be reported as an outage.
    private static bool Outside(Exception failure, CancellationToken cancellationToken) =>
        failure is HttpRequestException ||
        (failure is TaskCanceledException && !cancellationToken.IsCancellationRequested);

    private sealed record Door(string Name, string Route, string Payload);
}

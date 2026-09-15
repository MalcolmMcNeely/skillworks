using System.Net.Http.Json;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Ingest;

public static class IngestRequests
{
    public static async Task<IngestRow> Ask(this StudioHost studio, string route)
    {
        await studio.WaitForIngestPasses(1);

        using var response = await studio.Client.PostAsync(route, content: null);
        response.EnsureSuccessStatusCode();

        return await response.Content.ReadFromJsonAsync<IngestRow>(StudioHost.Wire)
            ?? throw new InvalidOperationException("The ingest status came back empty.");
    }

    public static async Task<IReadOnlyList<FaultRow>> Faults(this StudioHost studio)
    {
        await studio.WaitForIngestPasses(1);

        return await studio.Client.GetFromJsonAsync<FaultRow[]>("/api/ingest/faults", StudioHost.Wire) ?? [];
    }

    // The ingest's own count, as the activations list reads the events store, not what the ingest stored.
    public static async Task<int> ActivationsAdded(this StudioHost studio)
    {
        await studio.WaitForIngestPasses(1);

        return (await studio.Status()).ActivationsAdded;
    }

    // Polled often, as the next pass reports nothing added and would hide the pass that did.
    public static async Task WaitForActivationsAdded(this StudioHost studio)
    {
        var deadline = DateTime.UtcNow.AddSeconds(30);

        while (await studio.ActivationsAdded() == 0)
        {
            if (DateTime.UtcNow > deadline)
            {
                throw new TimeoutException("No pass ever added an activation.");
            }

            await Task.Delay(20);
        }
    }
}

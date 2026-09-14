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
}

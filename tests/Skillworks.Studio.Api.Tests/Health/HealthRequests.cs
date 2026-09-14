using System.Net.Http.Json;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Health;

public static class HealthRequests
{
    public static async Task<HealthRow> Health(this StudioHost studio)
    {
        await studio.WaitForIngestPasses(1);

        return await studio.Client.GetFromJsonAsync<HealthRow>("/api/health", StudioHost.Wire)
            ?? throw new InvalidOperationException("The health report came back empty.");
    }

    public static async Task<PartRow> Part(this StudioHost studio, string name) =>
        (await studio.Health()).Parts.Single(part => part.Name == name);
}

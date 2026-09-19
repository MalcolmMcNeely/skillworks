using System.Net.Http.Json;
using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Shared.Health;

public static class HealthRequests
{
    public static async Task<HealthRow> Health(this StudioHost studio) =>
        await studio.Client.GetFromJsonAsync<HealthRow>("/api/health", StudioHost.Wire)
        ?? throw new InvalidOperationException("The health report came back empty.");

    public static async Task<PartRow> Part(this StudioHost studio, string name) =>
        (await studio.Health()).Parts.Single(part => part.Name == name);

    // Raw JSON, as a typed row silently drops a field the answer should no longer carry.
    public static async Task<IReadOnlyList<string>> HealthFields(this StudioHost studio)
    {
        var answer = await studio.Client.GetFromJsonAsync<JsonObject>("/api/health", StudioHost.Wire);

        return [.. (answer ?? []).Select(field => field.Key).Order(StringComparer.Ordinal)];
    }
}

using System.Net.Http.Json;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Spend;

public static class SpendRequests
{
    public static async Task<IReadOnlyList<PriceRow>> Prices(this StudioHost studio)
    {
        return await studio.Client.GetFromJsonAsync<PriceRow[]>("/api/prices", StudioHost.Wire) ?? [];
    }

    public static async Task Reprice(this StudioHost studio, PriceRow price)
    {
        using var response = await studio.Client.PutAsJsonAsync("/api/prices", price, StudioHost.Wire);
        response.EnsureSuccessStatusCode();
    }
}

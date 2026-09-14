using System.Net.Http.Json;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Filters;

public static class FilterRequests
{
    public static async Task<FilterChoiceRow> Filters(this StudioHost studio)
    {
        await studio.WaitForIngestPasses(1);

        return await studio.Client.GetFromJsonAsync<FilterChoiceRow>("/api/filters", StudioHost.Wire)
            ?? throw new InvalidOperationException("The filter choices came back empty.");
    }
}

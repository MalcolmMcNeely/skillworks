using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Shared.Filters;

public static class FilterRequests
{
    public static Task<IReadOnlyList<JsonObject>> FilterChoiceLines(
        this StudioHost studio,
        string filter = "",
        int count = int.MaxValue,
        Task? closeAfter = null) =>
        studio.Lines($"/api/filters{filter}", count, closeAfter);

    public static async Task<FilterChoicesAnswer> FilterChoices(this StudioHost studio, string filter = "") =>
        FilterChoicesAnswer.Of(await studio.FilterChoiceLines(filter));
}

using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Shared.Harness;

namespace Skillworks.Studio.Api.Tests.Dashboard.Activations;

public static class ActivationRequests
{
    public static Task<IReadOnlyList<JsonObject>> ActivationLines(this StudioHost studio, string filter = "") =>
        studio.Lines($"/api/activations{filter}");

    public static async Task<ActivationsAnswer> ActivationAnswer(this StudioHost studio, string filter = "") =>
        ActivationsAnswer.Of(await studio.ActivationLines(filter));

    public static async Task<IReadOnlyList<ActivationRow>> ActivationsOf(this StudioHost studio, string filter = "") =>
        (await studio.ActivationAnswer(filter)).Activations;

    // Raw JSON, as a typed row silently drops a field the line should no longer carry.
    public static async Task<JsonObject> ActivationLine(this StudioHost studio, string kind, string filter = "") =>
        (await studio.ActivationLines(filter)).First(line => StudioHost.KindOf(line) == kind);
}

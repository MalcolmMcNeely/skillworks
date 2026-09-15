using System.Net.Http.Json;
using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Activations;

public static class ActivationRequests
{
    public static async Task<IReadOnlyList<ActivationRow>> Activations(this StudioHost studio, string filter = "") =>
        (await studio.ActivationList(filter)).Activations;

    public static async Task<ActivationsAnswer> ActivationList(this StudioHost studio, string filter = "") =>
        await studio.Client.GetFromJsonAsync<ActivationsAnswer>($"/api/activations{filter}", StudioHost.Wire)
            ?? throw new InvalidOperationException("The activation list came back empty.");

    public static async Task<ActivationRow> Activation(this StudioHost studio, string id) =>
        (await studio.OpenActivation(id)).Activation
            ?? throw new InvalidOperationException($"Activation {id} came back without its activation.");

    public static async Task<ActivationAnswer> OpenActivation(this StudioHost studio, string id) =>
        await studio.Client.GetFromJsonAsync<ActivationAnswer>(Opening(id), StudioHost.Wire)
            ?? throw new InvalidOperationException("The activation came back empty.");

    public static Task<HttpResponseMessage> AskForActivation(this StudioHost studio, string id) =>
        studio.Client.GetAsync(Opening(id));

    // Raw JSON, as a typed row silently drops a field the answer should no longer carry.
    public static async Task<IReadOnlyList<string>> ListedFields(this StudioHost studio)
    {
        var answer = await studio.Client.GetFromJsonAsync<JsonObject>("/api/activations", StudioHost.Wire);

        return StudioHost.Fields(answer?["activations"]?.AsArray().FirstOrDefault());
    }

    public static async Task<IReadOnlyList<string>> OpenedFields(this StudioHost studio, string id)
    {
        var answer = await studio.Client.GetFromJsonAsync<JsonObject>(Opening(id), StudioHost.Wire);

        return StudioHost.Fields(answer?["activation"]);
    }

    public static async Task<(IReadOnlyList<string> Answer, IReadOnlyList<string> Gap)> ListGapFields(this StudioHost studio)
    {
        var answer = await studio.Client.GetFromJsonAsync<JsonObject>("/api/activations", StudioHost.Wire);

        return (StudioHost.Fields(answer), StudioHost.Fields(answer?["gap"]));
    }

    public static async Task<(IReadOnlyList<string> Answer, IReadOnlyList<string> Gap)> OpenedGapFields(
        this StudioHost studio,
        string id)
    {
        var answer = await studio.Client.GetFromJsonAsync<JsonObject>(Opening(id), StudioHost.Wire);

        return (StudioHost.Fields(answer), StudioHost.Fields(answer?["gap"]));
    }

    private static string Opening(string id) => $"/api/activations/{Uri.EscapeDataString(id)}";
}

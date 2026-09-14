using System.Net.Http.Json;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Activations;

public static class ActivationRequests
{
    public static async Task<IReadOnlyList<ActivationRow>> Activations(this StudioHost studio, string filter = "") =>
        (await studio.ActivationList(filter)).Activations;

    public static async Task<ActivationsAnswer> ActivationList(this StudioHost studio, string filter = "")
    {
        await studio.WaitForIngestPasses(1);

        return await studio.Client.GetFromJsonAsync<ActivationsAnswer>($"/api/activations{filter}", StudioHost.Wire)
            ?? throw new InvalidOperationException("The activation list came back empty.");
    }

    public static async Task<ActivationDetailRow> Activation(this StudioHost studio, string id) =>
        (await studio.OpenActivation(id)).Activation;

    public static async Task<ActivationAnswer> OpenActivation(this StudioHost studio, string id)
    {
        await studio.WaitForIngestPasses(1);

        return await studio.Client.GetFromJsonAsync<ActivationAnswer>($"/api/activations/{id}", StudioHost.Wire)
            ?? throw new InvalidOperationException("The activation came back empty.");
    }

    public static async Task<HttpResponseMessage> AskForActivation(this StudioHost studio, string id)
    {
        await studio.WaitForIngestPasses(1);

        return await studio.Client.GetAsync($"/api/activations/{id}");
    }
}

using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Answers;
using Skillworks.Studio.Api.Tests.Sessions.Rows;

namespace Skillworks.Studio.Api.Tests.Sessions;

public static class SessionRequests
{
    // A count stops reading part way, which is how a test sees what the gate alone answered.
    public static Task<IReadOnlyList<JsonObject>> SessionLines(
        this StudioHost studio,
        string filter = "",
        int count = int.MaxValue) =>
        studio.Lines($"/api/sessions{filter}", count);

    public static async Task<SessionsAnswer> SessionAnswer(this StudioHost studio, string filter = "") =>
        SessionsAnswer.Of(await studio.SessionLines(filter));

    public static async Task<IReadOnlyList<SessionRow>> SessionsIn(this StudioHost studio, string filter = "") =>
        (await studio.SessionAnswer(filter)).Sessions;

    public static Task<HttpResponseMessage> AskForSessions(this StudioHost studio, string filter) =>
        studio.Client.GetAsync($"/api/sessions{filter}");

    // Raw JSON, as a typed row silently drops a field the line should no longer carry.
    public static async Task<JsonObject> SessionLine(this StudioHost studio, string kind, string filter = "") =>
        (await studio.SessionLines(filter)).First(line => StudioHost.KindOf(line) == kind);

    public static Task<IReadOnlyList<JsonObject>> StepLines(this StudioHost studio, string id, string filter = "") =>
        studio.Lines($"/api/sessions/{id}{filter}");

    // Stops reading part way, which is how a test sees what the events alone answered before the spans were asked for.
    public static Task<IReadOnlyList<JsonObject>> FirstStepLines(this StudioHost studio, string id, int count) =>
        studio.Lines($"/api/sessions/{id}", count);

    public static async Task<StepsAnswer> StepAnswer(this StudioHost studio, string id, string filter = "") =>
        StepsAnswer.Of(await studio.StepLines(id, filter));

    public static async Task<IReadOnlyList<StepRow>> StepsIn(this StudioHost studio, string id, string filter = "") =>
        (await studio.StepAnswer(id, filter)).Steps;

    public static async Task<IReadOnlyList<ExchangeRow>> ExchangesIn(this StudioHost studio, string id, string filter = "") =>
        (await studio.StepAnswer(id, filter)).Exchanges;

    public static async Task<IReadOnlyList<ActivationRow>> ActivationsIn(this StudioHost studio, string id, string filter = "") =>
        (await studio.StepAnswer(id, filter)).Activations;

    public static async Task<IReadOnlyList<ContextRow>> ContextIn(this StudioHost studio, string id, string filter = "") =>
        (await studio.StepAnswer(id, filter)).Context;

    public static async Task<IReadOnlyList<PartSpellRow>> PartsIn(this StudioHost studio, string id, string filter = "") =>
        (await studio.StepAnswer(id, filter)).Parts;

    public static async Task<IReadOnlyList<FindingRow>> FindingsIn(this StudioHost studio, string id, string filter = "") =>
        (await studio.StepAnswer(id, filter)).Findings;

    public static async Task<JsonObject> StepLine(this StudioHost studio, string kind, string id) =>
        (await studio.StepLines(id)).First(line => StudioHost.KindOf(line) == kind);
}

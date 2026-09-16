using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public static class SessionRequests
{
    public static Task<IReadOnlyList<JsonObject>> SessionLines(this StudioHost studio, string filter = "") =>
        studio.Lines($"/api/sessions{filter}");

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

    public static async Task<StepsAnswer> StepAnswer(this StudioHost studio, string id, string filter = "") =>
        StepsAnswer.Of(await studio.StepLines(id, filter));

    public static async Task<IReadOnlyList<StepRow>> StepsIn(this StudioHost studio, string id, string filter = "") =>
        (await studio.StepAnswer(id, filter)).Steps;

    public static async Task<JsonObject> StepLine(this StudioHost studio, string kind, string id) =>
        (await studio.StepLines(id)).First(line => StudioHost.KindOf(line) == kind);
}

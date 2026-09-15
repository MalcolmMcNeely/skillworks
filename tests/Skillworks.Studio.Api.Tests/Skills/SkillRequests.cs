using System.Net.Http.Json;
using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public static class SkillRequests
{
    public static async Task<IReadOnlyList<SkillRow>> Skills(this StudioHost studio, string filter = "") =>
        (await studio.SkillTable(filter)).Skills;

    public static async Task<SkillsAnswer> SkillTable(this StudioHost studio, string filter = "") =>
        await studio.Client.GetFromJsonAsync<SkillsAnswer>($"/api/skills{filter}", StudioHost.Wire)
            ?? throw new InvalidOperationException("The skill table came back empty.");

    public static Task<HttpResponseMessage> AskForSkills(this StudioHost studio, string filter) =>
        studio.Client.GetAsync($"/api/skills{filter}");

    public static async Task<SkillRow> Skill(this StudioHost studio, string name, string filter = "") =>
        (await studio.Skills(filter)).Single(skill => skill.Name == name);

    public static async Task<int> ActivationsOf(this StudioHost studio, string name, string filter = "") =>
        (await studio.Skills(filter)).SingleOrDefault(skill => skill.Name == name)?.Activations ?? 0;

    // Raw JSON, as a typed row silently drops a field the answer should no longer carry.
    public static async Task<(IReadOnlyList<string> Answer, IReadOnlyList<string> Gap)> SkillTableGapFields(this StudioHost studio)
    {
        var answer = await studio.Client.GetFromJsonAsync<JsonObject>("/api/skills", StudioHost.Wire);

        return (StudioHost.Fields(answer), StudioHost.Fields(answer?["gap"]));
    }
}

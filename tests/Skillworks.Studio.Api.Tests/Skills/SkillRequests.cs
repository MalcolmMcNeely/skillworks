using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Skills;

public static class SkillRequests
{
    public static Task<IReadOnlyList<JsonObject>> SkillLines(this StudioHost studio, string filter = "") =>
        studio.Lines($"/api/skills{filter}");

    public static async Task<SkillsAnswer> SkillAnswer(this StudioHost studio, string filter = "") =>
        SkillsAnswer.Of(await studio.SkillLines(filter));

    public static async Task<IReadOnlyList<SkillRow>> SkillsOn(this StudioHost studio, string day, string filter = "") =>
        (await studio.SkillAnswer(filter)).Day(day).Skills;

    public static async Task<SkillRow> SkillOn(this StudioHost studio, string day, string name, string filter = "") =>
        (await studio.SkillsOn(day, filter)).Single(skill => skill.Name == name);

    public static Task<HttpResponseMessage> AskForSkills(this StudioHost studio, string filter) =>
        studio.Client.GetAsync($"/api/skills{filter}");

    // Raw JSON, as a typed row silently drops a field the line should no longer carry.
    public static async Task<JsonObject> SkillLine(this StudioHost studio, string kind, string filter = "") =>
        (await studio.SkillLines(filter)).First(line => SkillsAnswer.KindOf(line) == kind);
}

using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Gaps;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed record StepsAnswer(
    SessionRow? Run,
    IReadOnlyList<StepRow> Steps,
    IReadOnlyList<ExchangeRow> Exchanges,
    IReadOnlyList<SkillCallRow> SkillCalls,
    IReadOnlyList<ContextRow> Context,
    long? LimitTokens,
    GapRow Gap)
{
    public static StepsAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        Opened(lines.Single(line => StudioHost.KindOf(line) == "head")),
        Held<StepRow>(lines, "steps"),
        Held<ExchangeRow>(lines, "exchanges"),
        Held<SkillCallRow>(lines, "skillCalls"),
        Held<ContextRow>(lines, "context", "points"),
        Limit(lines),
        StudioHost.Read<GapRow>(lines.Single(line => StudioHost.KindOf(line) == "end")["gap"]));

    private static IReadOnlyList<T> Held<T>(IReadOnlyList<JsonObject> lines, string kind, string? field = null) =>
    [
        .. lines
            .Where(line => StudioHost.KindOf(line) == kind)
            .SelectMany(line => line[field ?? kind]?.AsArray() ?? [])
            .Select(StudioHost.Read<T>)
    ];

    private static long? Limit(IReadOnlyList<JsonObject> lines) =>
        lines.Where(line => StudioHost.KindOf(line) == "context").Select(line => (long?)line["limitTokens"]).FirstOrDefault();

    private static SessionRow? Opened(JsonObject head) =>
        head["session"] is { } session ? StudioHost.Read<SessionRow>(session) : null;
}

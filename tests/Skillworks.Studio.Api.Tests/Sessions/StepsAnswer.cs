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
    string? Depth,
    IReadOnlyDictionary<string, string> Agents,
    GapRow Events,
    GapRow Traces)
{
    public static StepsAnswer Of(IReadOnlyList<JsonObject> lines)
    {
        var spans = Line(lines, "agents");

        return new StepsAnswer(
            Opened(lines.Single(line => StudioHost.KindOf(line) == "head")),
            Held<StepRow>(lines, "steps"),
            Held<ExchangeRow>(lines, "exchanges"),
            Held<SkillCallRow>(lines, "skillCalls"),
            Held<ContextRow>(lines, "context", "points"),
            Limit(lines),
            (string?)spans?["depth"],
            spans is null
                ? new Dictionary<string, string>()
                : StudioHost.Read<Dictionary<string, string>>(spans["agents"]),
            Store(lines, "events"),
            Store(lines, "traces"));
    }

    private static IReadOnlyList<T> Held<T>(IReadOnlyList<JsonObject> lines, string kind, string? field = null) =>
    [
        .. lines
            .Where(line => StudioHost.KindOf(line) == kind)
            .SelectMany(line => line[field ?? kind]?.AsArray() ?? [])
            .Select(StudioHost.Read<T>)
    ];

    private static long? Limit(IReadOnlyList<JsonObject> lines) =>
        lines.Where(line => StudioHost.KindOf(line) == "context").Select(line => (long?)line["limitTokens"]).FirstOrDefault();

    private static JsonObject? Line(IReadOnlyList<JsonObject> lines, string kind) =>
        lines.FirstOrDefault(line => StudioHost.KindOf(line) == kind);

    private static GapRow Store(IReadOnlyList<JsonObject> lines, string store) =>
        StudioHost.Read<GapRow>(lines.Single(line => StudioHost.KindOf(line) == "end")[store]);

    private static SessionRow? Opened(JsonObject head) =>
        head["session"] is { } session ? StudioHost.Read<SessionRow>(session) : null;
}

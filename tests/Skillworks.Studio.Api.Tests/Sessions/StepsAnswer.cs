using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Gaps;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed record StepsAnswer(SessionRow? Run, IReadOnlyList<StepRow> Steps, GapRow Gap)
{
    public static StepsAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        Opened(lines.Single(line => StudioHost.KindOf(line) == "head")),
        [
            .. lines
                .Where(line => StudioHost.KindOf(line) == "steps")
                .SelectMany(line => line["steps"]?.AsArray() ?? [])
                .Select(StudioHost.Read<StepRow>)
        ],
        StudioHost.Read<GapRow>(lines.Single(line => StudioHost.KindOf(line) == "end")["gap"]));

    private static SessionRow? Opened(JsonObject head) =>
        head["session"] is { } session ? StudioHost.Read<SessionRow>(session) : null;
}

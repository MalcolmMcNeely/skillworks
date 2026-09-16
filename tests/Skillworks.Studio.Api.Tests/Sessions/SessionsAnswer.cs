using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Gaps;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Sessions;

public sealed record SessionsAnswer(SessionsHeadRow Head, IReadOnlyList<SessionRow> Sessions, GapRow Gap)
{
    public static SessionsAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        StudioHost.Read<SessionsHeadRow>(lines.Single(line => StudioHost.KindOf(line) == "head")),
        [
            .. lines
                .Where(line => StudioHost.KindOf(line) == "sessions")
                .SelectMany(line => line["sessions"]?.AsArray() ?? [])
                .Select(StudioHost.Read<SessionRow>)
        ],
        StudioHost.Read<GapRow>(lines.Single(line => StudioHost.KindOf(line) == "end")["gap"]));
}

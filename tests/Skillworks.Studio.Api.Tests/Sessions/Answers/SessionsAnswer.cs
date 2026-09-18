using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Gaps;
using Skillworks.Studio.Api.Tests.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows;

namespace Skillworks.Studio.Api.Tests.Sessions.Answers;

public sealed record SessionsAnswer(
    SessionsHeadRow Head,
    IReadOnlyList<SessionRow> Sessions,
    IReadOnlyDictionary<string, IReadOnlyDictionary<string, decimal>> Measures,
    GapRow Gap)
{
    // Read on their own as well, so a test that stops before the end line still sees the rows.
    public static IReadOnlyList<SessionRow> RowsIn(IReadOnlyList<JsonObject> lines) =>
    [
        .. lines
            .Where(line => StudioHost.KindOf(line) == "sessions")
            .SelectMany(line => line["sessions"]?.AsArray() ?? [])
            .Select(StudioHost.Read<SessionRow>)
    ];

    public static SessionsAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        StudioHost.Read<SessionsHeadRow>(lines.Single(line => StudioHost.KindOf(line) == "head")),
        RowsIn(lines),
        lines
            .Where(line => StudioHost.KindOf(line) == "measure")
            .ToDictionary(
                line => (string?)line["measure"] ?? "",
                line => StudioHost.Read<IReadOnlyDictionary<string, decimal>>(line["values"]),
                StringComparer.Ordinal),
        StudioHost.Read<GapRow>(lines.Single(line => StudioHost.KindOf(line) == "end")["gap"]));

    public decimal Measured(string measure, string id) => Measures[measure].GetValueOrDefault(id);
}

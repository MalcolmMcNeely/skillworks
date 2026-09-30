using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Shared.Gaps;
using Skillworks.Studio.Api.Tests.Shared.Harness;
using Skillworks.Studio.Api.Tests.Sessions.Rows;

namespace Skillworks.Studio.Api.Tests.Sessions.Answers;

public sealed record SessionsAnswer(
    SessionsHeadRow Head,
    IReadOnlyList<SessionRow> Sessions,
    IReadOnlyDictionary<string, IReadOnlyDictionary<string, decimal>> Measures,
    // Empty when no line of Depths came, so a row it names nothing for reads as a dash either way.
    IReadOnlyDictionary<string, string> Depths,
    GapRow Gap,
    DateTimeOffset? OldestLatestUtc,
    DateTimeOffset? LookedBackToUtc)
{
    // Read on their own as well, so a test that stops before the end line still sees the rows.
    public static IReadOnlyList<SessionRow> RowsIn(IReadOnlyList<JsonObject> lines) =>
    [
        .. lines
            .Where(line => StudioHost.KindOf(line) == "sessions")
            .SelectMany(line => line["sessions"]?.AsArray() ?? [])
            .Select(StudioHost.Read<SessionRow>)
    ];

    public static SessionsAnswer Of(IReadOnlyList<JsonObject> lines)
    {
        var end = lines.Single(line => StudioHost.KindOf(line) == "end");

        return new(
            StudioHost.Read<SessionsHeadRow>(lines.Single(line => StudioHost.KindOf(line) == "head")),
            RowsIn(lines),
            lines
                .Where(line => StudioHost.KindOf(line) == "measure")
                .ToDictionary(
                    line => (string?)line["measure"] ?? "",
                    line => StudioHost.Read<IReadOnlyDictionary<string, decimal>>(line["values"]),
                    StringComparer.Ordinal),
            lines
                .Where(line => StudioHost.KindOf(line) == "depths")
                .Select(line => StudioHost.Read<IReadOnlyDictionary<string, string>>(line["depths"]))
                .SingleOrDefault() ?? new Dictionary<string, string>(),
            StudioHost.Read<GapRow>(end["gap"]),
            end["oldestLatestUtc"]?.GetValue<DateTimeOffset>(),
            end["lookedBackToUtc"]?.GetValue<DateTimeOffset>());
    }

    public decimal Measured(string measure, string id) => Measures[measure].GetValueOrDefault(id);
}

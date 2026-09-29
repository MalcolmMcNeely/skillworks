using System.Globalization;
using System.Text.Json.Nodes;

namespace Skillworks.Core.Tests.Shared.Stores.TraceStore;

// One Step as Claude Code sends it with CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 and traces exporting.
public sealed record RecordedSpan(
    string Name,
    string At,
    string Until,
    string Id,
    string? Parent = null,
    string? Agent = null,
    string? ToolUse = null,
    string? Request = null,
    string? StopReason = null,
    string? Attempt = null,
    IReadOnlyDictionary<string, string>? Output = null)
{
    internal JsonObject Record(string trace, string session)
    {
        var span = new JsonObject
        {
            ["traceId"] = trace,
            ["spanId"] = Id,
            ["name"] = Name,
            ["kind"] = 1,
            ["startTimeUnixNano"] = Nanoseconds(At),
            ["endTimeUnixNano"] = Nanoseconds(Until),
            ["attributes"] = Attributes(session),
        };

        // A root span has no parent, and OTLP has no value that means absent.
        if (Parent is not null)
        {
            span["parentSpanId"] = Parent;
        }

        if (Output is not null)
        {
            span["events"] = new JsonArray(
                new JsonObject
                {
                    ["timeUnixNano"] = Nanoseconds(Until),
                    ["name"] = "tool.output",
                    ["attributes"] = Pairs(Output.Select(pair => (pair.Key, (string?)pair.Value))),
                });
        }

        return span;
    }

    private JsonArray Attributes(string session) =>
        Pairs(
        [
            ("session.id", session),
            ("agent_id", Agent),
            ("tool_use_id", ToolUse),
            ("request_id", Request),
            ("stop_reason", StopReason),
            ("attempt", Attempt),
        ]);

    private static JsonArray Pairs(IEnumerable<(string Key, string? Value)> pairs) =>
    [
        .. pairs
            .Where(attribute => attribute.Value is not null)
            .Select(attribute => new JsonObject
            {
                ["key"] = attribute.Key,
                ["value"] = new JsonObject { ["stringValue"] = attribute.Value },
            })
    ];

    private static string Nanoseconds(string moment) =>
        ((DateTimeOffset.Parse(moment, CultureInfo.InvariantCulture).UtcTicks - DateTimeOffset.UnixEpoch.UtcTicks) * 100)
        .ToString(CultureInfo.InvariantCulture);
}

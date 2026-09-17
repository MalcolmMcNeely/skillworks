using Skillworks.Core.Sessions.Agents;
using Skillworks.Core.TraceStore;

namespace Skillworks.Core.Sessions.Trace;

public static class SpanTree
{
    // A Step left out ran inside nothing, and so sits at the root.
    public static IReadOnlyDictionary<string, string> Inside(
        IReadOnlyList<Span> spans,
        IReadOnlyList<StepKey> keys)
    {
        var bySpanId = BySpanId(spans);
        var byKey = ByKey(spans);
        var stepOfKey = StepOfKey(keys);
        var inside = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var key in keys)
        {
            if (byKey.GetValueOrDefault(key.Key) is { } span &&
                Outer(bySpanId, span) is { } outer &&
                stepOfKey.GetValueOrDefault(outer) is { } step &&
                !string.Equals(step, key.Step, StringComparison.Ordinal))
            {
                inside[key.Step] = step;
            }
        }

        return inside;
    }

    private static Dictionary<string, Span> BySpanId(IReadOnlyList<Span> spans)
    {
        var bySpanId = new Dictionary<string, Span>(StringComparer.Ordinal);

        foreach (var span in spans)
        {
            bySpanId[span.SpanId] = span;
        }

        return bySpanId;
    }

    private static Dictionary<string, Span> ByKey(IReadOnlyList<Span> spans)
    {
        var byKey = new Dictionary<string, Span>(StringComparer.Ordinal);

        foreach (var span in spans)
        {
            if (StepKey.Of(span) is { } key)
            {
                byKey[key] = span;
            }
        }

        return byKey;
    }

    // A request writes both a Turn and the answer it wrote, so the first of them is the Step above.
    private static Dictionary<string, string> StepOfKey(IReadOnlyList<StepKey> keys)
    {
        var stepOfKey = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var key in keys)
        {
            stepOfKey.TryAdd(key.Key, key.Step);
        }

        return stepOfKey;
    }

    // Claude Code wraps a Subagent's run in a Span that stands for no Step, so the walk climbs past it.
    private static string? Outer(IReadOnlyDictionary<string, Span> bySpanId, Span span)
    {
        var walked = new HashSet<string>(StringComparer.Ordinal) { span.SpanId };
        var above = span.ParentSpanId;

        while (above is not null && walked.Add(above) && bySpanId.GetValueOrDefault(above) is { } outer)
        {
            if (StepKey.Of(outer) is { } key)
            {
                return key;
            }

            above = outer.ParentSpanId;
        }

        return null;
    }
}

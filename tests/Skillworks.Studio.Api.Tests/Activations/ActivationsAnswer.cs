using System.Text.Json.Nodes;
using Skillworks.Studio.Api.Tests.Gaps;
using Skillworks.Studio.Api.Tests.Harness;

namespace Skillworks.Studio.Api.Tests.Activations;

public sealed record ActivationsAnswer(IReadOnlyList<ActivationRow> Activations, GapRow Gap)
{
    public static ActivationsAnswer Of(IReadOnlyList<JsonObject> lines) => new(
        [
            .. lines
                .Where(line => StudioHost.KindOf(line) == "activations")
                .SelectMany(line => line["activations"]?.AsArray() ?? [])
                .Select(StudioHost.Read<ActivationRow>)
        ],
        StudioHost.Read<GapRow>(lines.Single(line => StudioHost.KindOf(line) == "end")["gap"]));
}

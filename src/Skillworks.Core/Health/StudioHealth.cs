using Microsoft.Extensions.Options;
using Skillworks.Core.Catalogue;
using Skillworks.Core.EventsStore;
using Skillworks.Core.Telemetry;

namespace Skillworks.Core.Health;

public sealed class StudioHealth(
    CatalogueLocator catalogue,
    EventsStoreReader events,
    TelemetrySwitch telemetry,
    IOptions<LokiOptions> loki)
{
    public async Task<HealthReport> ReportAsync(CancellationToken cancellationToken)
    {
        var unreachable = await events.UnreachableAsync(cancellationToken);
        var emitting = telemetry.State();

        return new HealthReport(
            [
                Events(unreachable),
                Switch(emitting),
                Catalogue(catalogue.Locate()),
            ]);
    }

    private StudioPart Events(string? unreachable) => unreachable is null
        ? new StudioPart("Events store", PartState.Working, $"{loki.Value.ResolvedAddress()} answered.", null)
        : new StudioPart(
            "Events store",
            PartState.Broken,
            unreachable,
            "Start Studio's containers with aspire run. Until then, nothing Studio measures can be shown.");

    private static StudioPart Switch(TelemetrySwitchState state) => state switch
    {
        { Readable: false } => new StudioPart(
            "Claude Code telemetry",
            PartState.Broken,
            $"Studio cannot read {state.SettingsPath}: {state.Problem ?? "it could not be parsed"}.",
            "Fix that file by hand, or move it aside. Studio will not write a document it could not parse."),

        { Emitting: true } => new StudioPart(
            "Claude Code telemetry",
            PartState.Working,
            $"Claude Code is emitting to {state.CollectorEndpoint}.",
            null),

        _ => new StudioPart(
            "Claude Code telemetry",
            PartState.Off,
            "Claude Code is not emitting telemetry, so nothing new reaches the events store.",
            TelemetrySwitch.TurnOnNote),
    };

    private static StudioPart Catalogue(CatalogueLocation location) => location.Exists
        ? new StudioPart("Catalogue", PartState.Working, $"Reading skills from {location.Path}.", null)
        : new StudioPart(
            "Catalogue",
            PartState.Broken,
            $"There is no catalogue at {location.Path}.",
            "Point Catalogue:Path at it. Without it, a skill that has never fired is not listed at all.");
}

using Microsoft.Extensions.Options;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Provenance;
using Skillworks.Core.Settings;
using Skillworks.Core.Telemetry;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Health;

public enum PartState
{
    Working,
    Starting,
    Off,
    Broken,
}

public sealed record StudioPart(string Name, PartState State, string Detail, string? Action);

// WhyEmpty covers the transcript half only: provenance explains its own gaps in its ProvenanceNote.
public sealed record HealthReport(IReadOnlyList<StudioPart> Parts, string? WhyEmpty);

public sealed class StudioHealth(
    TranscriptLocator transcripts,
    CatalogueLocator catalogue,
    IngestReport ingest,
    SkillEvents events,
    TelemetrySwitch telemetry,
    IOptions<LokiOptions> loki,
    TimeProvider clock)
{
    // The real provenance query over a short window: a readiness route would pass a store that refuses it.
    private static readonly TimeSpan Probe = TimeSpan.FromMinutes(1);

    private const string PointAtTranscripts =
        "Point Transcripts:Path at the folder Claude Code writes its session files to.";

    public async Task<HealthReport> ReportAsync(CancellationToken cancellationToken)
    {
        var now = clock.GetUtcNow();
        var sessions = transcripts.Locate();
        var store = await ingest.StatusAsync(cancellationToken);
        var probed = await events.ReadAsync(now - Probe, now, cancellationToken);
        var emitting = telemetry.State();

        return new HealthReport(
            [
                Transcripts(sessions),
                Store(store),
                Events(probed.Unreachable),
                Switch(emitting),
                Catalogue(catalogue.Locate()),
            ],
            WhyEmpty(sessions, store));
    }

    private static StudioPart Transcripts(TranscriptLocation sessions) => sessions.Exists
        ? new StudioPart("Transcripts", PartState.Working, $"Reading session files from {sessions.Path}.", null)
        : new StudioPart("Transcripts", PartState.Broken, NoFolderAt(sessions.Path), PointAtTranscripts);

    private static StudioPart Store(IngestStatus status) => status switch
    {
        { CompletedPasses: 0 } => new StudioPart(
            "Telemetry store",
            PartState.Starting,
            "The first read of the transcripts has not finished, so the numbers are not all in yet.",
            null),

        { Faults: > 0 } => new StudioPart(
            "Telemetry store",
            PartState.Working,
            $"{Counted(status.TranscriptsTotal, "transcript")} read, stepping over " +
            $"{Counted(status.Faults, "piece")} it could not parse.",
            "Open the ingest panel to read what was skipped."),

        _ => new StudioPart(
            "Telemetry store",
            PartState.Working,
            $"{Counted(status.TranscriptsTotal, "transcript")} read.",
            null),
    };

    private static string Counted(int count, string thing) => $"{count} {thing}{(count == 1 ? "" : "s")}";

    private static string NoFolderAt(string path) => $"There is no folder at {path}.";

    private StudioPart Events(string? unreachable) => unreachable is null
        ? new StudioPart("Events store", PartState.Working, $"{loki.Value.ResolvedAddress()} answered.", null)
        : new StudioPart(
            "Events store",
            PartState.Broken,
            unreachable,
            "Start Studio's containers with aspire run. Counts and cost are unaffected: they come " +
            "from the transcripts. Only where a skill came from is lost.");

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

    private static string? WhyEmpty(TranscriptLocation sessions, IngestStatus status) => (sessions, status) switch
    {
        ({ Exists: false }, _) =>
            $"Studio has no transcripts to read. {NoFolderAt(sessions.Path)} {PointAtTranscripts}",

        (_, { CompletedPasses: 0 }) =>
            "Studio has not finished its first read of the transcripts, so this is not the whole " +
            "answer yet. Wait for the ingest to finish.",

        (_, { TranscriptsTotal: 0 }) =>
            $"There are no transcripts in {sessions.Path}. Run a Claude Code session, then ask " +
            "Studio to look for new sessions.",

        _ => null,
    };
}

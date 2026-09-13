using Microsoft.Extensions.Options;
using Skillworks.Core.Catalogue;
using Skillworks.Core.Provenance;
using Skillworks.Core.Settings;
using Skillworks.Core.Telemetry;
using Skillworks.Core.Transcripts;

namespace Skillworks.Core.Health;

/// <summary>How one part of Studio is doing.</summary>
public enum PartState
{
    /// <summary>Doing its job.</summary>
    Working,

    /// <summary>On its way and not ready yet. Nothing to do but wait.</summary>
    Starting,

    /// <summary>Deliberately not on. Nothing is broken, and something is missing because of it.</summary>
    Off,

    /// <summary>Meant to be working and is not.</summary>
    Broken,
}

/// <summary>One part of Studio: how it is doing, and what a developer would do about it.</summary>
/// <param name="Detail">What is true right now, named concretely enough to act on: a path, a count.</param>
/// <param name="Action">What a developer would do next, or null when there is nothing to do.</param>
public sealed record StudioPart(string Name, PartState State, string Detail, string? Action);

/// <summary>
/// Every part of Studio in one place, so an empty screen is explained rather than mysterious.
/// </summary>
/// <param name="WhyEmpty">
/// Why a view built from the transcripts has nothing in it, naming the source that is missing and
/// the action that would fix it — or null when the transcript half is healthy and an empty view
/// simply means an empty history. Provenance says why it is empty for itself, on the note that
/// travels with every answer.
/// </param>
public sealed record HealthReport(IReadOnlyList<StudioPart> Parts, string? WhyEmpty);

/// <summary>
/// The health of each half of Studio and of the things either half needs. It is read on demand
/// rather than watched, because every part of it is a question Studio can only answer by asking:
/// a folder is there or it is not, and a container is up or it is not.
/// </summary>
public sealed class StudioHealth(
    TranscriptLocator transcripts,
    CatalogueLocator catalogue,
    IngestReport ingest,
    SkillEvents events,
    TelemetrySwitch telemetry,
    IOptions<LokiOptions> loki,
    TimeProvider clock)
{
    /// <summary>
    /// How far back the probe asks. Short, because what is wanted is whether the store answers at
    /// all. It is the same question every provenance view asks, and deliberately so: a cheaper
    /// route that only reported readiness would call a store healthy while it refused the one query
    /// the rest of Studio makes.
    /// </summary>
    private static readonly TimeSpan Probe = TimeSpan.FromMinutes(1);

    /// <summary>
    /// Said in one place, because the part and the reason a view is empty are the same fact and a
    /// reader who met two spellings of it would wonder whether they were two problems.
    /// </summary>
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

    /// <summary>The session files on disk: the durable record, and the half that stands on its own.</summary>
    private static StudioPart Transcripts(TranscriptLocation sessions) => sessions.Exists
        ? new StudioPart("Transcripts", PartState.Working, $"Reading session files from {sessions.Path}.", null)
        : new StudioPart("Transcripts", PartState.Broken, NoFolderAt(sessions.Path), PointAtTranscripts);

    /// <summary>Studio's own store of what it has read, and how much of the history is in it.</summary>
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

    /// <summary>
    /// The events store, asked directly rather than inferred from an empty answer. An outage and a
    /// quiet period look the same in a list of events and must never read the same on a screen.
    /// </summary>
    private StudioPart Events(string? unreachable) => unreachable is null
        ? new StudioPart("Events store", PartState.Working, $"{loki.Value.ResolvedAddress()} answered.", null)
        : new StudioPart(
            "Events store",
            PartState.Broken,
            unreachable,
            "Start Studio's containers with aspire run. Counts and cost are unaffected: they come " +
            "from the transcripts. Only where a skill came from is lost.");

    /// <summary>Whether Claude Code is filling the events store, which is the other half of provenance.</summary>
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

    /// <summary>The catalogue, which is where a skill that has never fired comes from.</summary>
    private static StudioPart Catalogue(CatalogueLocation location) => location.Exists
        ? new StudioPart("Catalogue", PartState.Working, $"Reading skills from {location.Path}.", null)
        : new StudioPart(
            "Catalogue",
            PartState.Broken,
            $"There is no catalogue at {location.Path}.",
            "Point Catalogue:Path at it. Without it, a skill that has never fired is not listed at all.");

    /// <summary>
    /// Why the transcript half has nothing to show. In the order a developer would check: there is
    /// nowhere to read from, there has not been time to read it, or there is nothing there to read.
    /// Null means the half is healthy and an empty table is an honest empty history.
    /// </summary>
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

namespace Skillworks.Core.Provenance;

// Trigger stays verbatim (claude-proactive, user-slash): putting it into words is the screen's job.
public sealed record SkillOrigin(string? Trigger, string? Source, string? Plugin, string? Marketplace)
{
    private const string TriggerAttribute = "invocation_trigger";

    private const string SourceAttribute = "skill.source";

    private const string PluginAttribute = "plugin.name";

    private const string MarketplaceAttribute = "marketplace.name";

    private const string PluginSource = "plugin";

    internal static readonly IReadOnlyList<string> Attributes =
        [TriggerAttribute, SourceAttribute, PluginAttribute, MarketplaceAttribute];

    internal bool DeliveredByPlugin => Source == PluginSource;

    internal static SkillOrigin Of(Func<string, string?> attribute) =>
        new(attribute(TriggerAttribute), attribute(SourceAttribute), attribute(PluginAttribute), attribute(MarketplaceAttribute));

    internal static IReadOnlyList<SkillOrigin> Ordered(IEnumerable<SkillOrigin> origins) =>
    [
        .. origins
            .Distinct()
            .OrderBy(origin => origin.Marketplace, StringComparer.OrdinalIgnoreCase)
            .ThenBy(origin => origin.Plugin, StringComparer.OrdinalIgnoreCase)
            .ThenBy(origin => origin.Trigger, StringComparer.OrdinalIgnoreCase)
    ];
}

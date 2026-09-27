using Skillworks.Core.Shared.Filters;
using Skillworks.Core.Shared.Stores.TraceStore;

namespace Skillworks.Core.Sessions.DepthColumn;

// The read rides beside the Depths, so a row left without one is explained by the store that fell short.
public sealed record DepthLanding(IReadOnlyDictionary<string, Depth> Depths, TracedSessions Traced);

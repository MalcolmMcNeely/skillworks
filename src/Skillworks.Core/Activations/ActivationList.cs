using Skillworks.Core.Filters;
using Skillworks.Core.Gaps;

namespace Skillworks.Core.Activations;

public sealed record ActivationList(
    IReadOnlyList<Activation> Activations,
    Gap Gap,
    DaySpan Span);

using Skillworks.Core.Activations;
using Skillworks.Core.Spend;

namespace Skillworks.Core.Ingest.Parsing;

internal readonly record struct LineReading(
    IReadOnlyList<Activation> Activations,
    Turn? Turn,
    string? Problem);

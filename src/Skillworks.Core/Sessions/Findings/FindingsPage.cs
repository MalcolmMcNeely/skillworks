using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.Findings;

public sealed record FindingsPage(IReadOnlyList<Finding> Findings) : ArrivingLine("findings");

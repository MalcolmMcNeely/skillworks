using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions;

public sealed record SessionsPage(IReadOnlyList<SessionRow> Sessions) : ArrivingLine("sessions");

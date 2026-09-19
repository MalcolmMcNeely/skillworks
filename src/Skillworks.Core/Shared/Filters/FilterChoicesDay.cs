using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Shared.Filters;

public sealed record FilterChoicesDay(DateOnly Day, IReadOnlyList<string> Repositories) : ArrivingLine("day");

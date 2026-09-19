using Skillworks.Core.Shared.Arriving;

namespace Skillworks.Core.Sessions.Steps;

public sealed record StepsPage(IReadOnlyList<Step> Steps) : ArrivingLine("steps");

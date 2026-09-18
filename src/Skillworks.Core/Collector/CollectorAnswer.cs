namespace Skillworks.Core.Collector;

public sealed record CollectorAnswer(CollectorState State, string Detail)
{
    public static CollectorAnswer Answering(Uri address) =>
        new(CollectorState.Answering, $"{address} answered on every door.");

    public static CollectorAnswer Shut(string detail) => new(CollectorState.Shut, detail);
}

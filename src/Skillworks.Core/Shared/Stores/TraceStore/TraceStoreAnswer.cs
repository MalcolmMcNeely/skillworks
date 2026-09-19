namespace Skillworks.Core.Shared.Stores.TraceStore;

public sealed record TraceStoreAnswer(TraceStoreState State, string Detail)
{
    public static TraceStoreAnswer Answering(Uri address) =>
        new(TraceStoreState.Answering, $"{address} answered.");

    // Tempo refuses reads until it has replayed its log, and a store that is coming up is nobody's fault.
    public static TraceStoreAnswer Starting(string detail) => new(TraceStoreState.Starting, detail);

    public static TraceStoreAnswer Unreachable(string detail) => new(TraceStoreState.Unreachable, detail);
}

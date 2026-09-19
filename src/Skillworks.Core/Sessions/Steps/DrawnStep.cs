using Skillworks.Core.Shared.Stores.EventsStore;

namespace Skillworks.Core.Sessions.Steps;

// The event a Step was drawn from, kept beside it, as a Turn's cost and an uncut answer are on the event alone.
public sealed record DrawnStep(EventLine Line, Step Step);

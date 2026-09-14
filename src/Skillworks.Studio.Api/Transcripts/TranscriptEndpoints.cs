using Skillworks.Core.Transcripts;

namespace Skillworks.Studio.Api.Transcripts;

public static class TranscriptEndpoints
{
    public static IEndpointRouteBuilder MapTranscriptEndpoints(this IEndpointRouteBuilder api)
    {
        api.MapGet("transcripts", (TranscriptLocator locator) => locator.Locate());

        return api;
    }
}

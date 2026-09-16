using Skillworks.Core.Telemetry;

namespace Skillworks.Studio.Api.Telemetry;

public static class TelemetrySwitchEndpoints
{
    public static IEndpointRouteBuilder MapTelemetrySwitchEndpoints(this IEndpointRouteBuilder api)
    {
        // The GET carries the file a team would commit, so the front end can show it without a second call.
        api.MapGet("telemetry/switch", (TelemetrySwitch telemetry) => telemetry.State());

        api.MapPut("telemetry/switch", (TelemetrySwitchRequest request, TelemetrySwitch telemetry) =>
        {
            var result = request.Emitting ? telemetry.TurnOn() : telemetry.TurnOff();

            // A conflict, not a bad request: the settings on disk must change before the same call can succeed.
            return result.Refusal is null
                ? Results.Ok(result.State)
                : Results.Problem(result.Refusal, statusCode: StatusCodes.Status409Conflict);
        });

        return api;
    }
}

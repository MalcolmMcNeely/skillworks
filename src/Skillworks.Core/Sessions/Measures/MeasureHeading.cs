namespace Skillworks.Core.Sessions.Measures;

// A person reads a Gap, so a Measure is named there as its column heads it, not as the wire spells it.
public static class MeasureHeading
{
    public static string Of(Measure measure) => measure switch
    {
        Measure.ToolCalls => "Tool calls",
        Measure.Cost => "Cost",
        Measure.Faults => "Faults",
        Measure.Friction => "Friction",

        // A Measure nobody wrote a heading for is named as it is spelled, never as another Measure.
        _ => measure.ToString(),
    };
}

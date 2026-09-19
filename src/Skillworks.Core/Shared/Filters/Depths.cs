namespace Skillworks.Core.Shared.Filters;

// Both halves or Thin, in one place, so asking the table for Full runs and opening one cannot disagree.
public static class Depths
{
    public static Depth Of(bool traced, bool withheld) => traced && !withheld ? Depth.Full : Depth.Thin;
}

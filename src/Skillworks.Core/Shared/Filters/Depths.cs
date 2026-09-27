namespace Skillworks.Core.Shared.Filters;

// Both halves or Thin, in one place, so a row of the Sessions list and the Session it opens cannot disagree.
public static class Depths
{
    public static Depth Of(bool traced, bool withheld) => traced && !withheld ? Depth.Full : Depth.Thin;
}

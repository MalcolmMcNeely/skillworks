using Skillworks.Architecture.Comments;
using Skillworks.Architecture.Placement;
using Skillworks.Architecture.RulesFiles;

namespace Skillworks.Architecture;

internal sealed record Rules(PlacementRules Placement, CommentRules Comments, IReadOnlyList<Breach> Breaches)
{
    public static Rules Read(string root)
    {
        var placementFile = RulesFile.Load(root, PlacementRules.RelativePath);
        var commentsFile = RulesFile.Load(root, CommentRules.RelativePath);

        var placement = PlacementRules.Read(placementFile);
        var comments = CommentRules.Read(commentsFile);

        return new(placement, comments, [.. placementFile.Breaches, .. commentsFile.Breaches]);
    }
}

using Skillworks.Architecture.Comments;
using Skillworks.Architecture.Placement;
using Skillworks.Architecture.RulesFiles;
using Skillworks.Architecture.Words;

namespace Skillworks.Architecture;

internal sealed record Rules(
    PlacementRules Placement,
    CommentRules Comments,
    WordRules Words,
    IReadOnlyList<Breach> Breaches)
{
    public static Rules Read(string root)
    {
        var placementFile = RulesFile.Load(root, PlacementRules.RelativePath);
        var commentsFile = RulesFile.Load(root, CommentRules.RelativePath);
        var wordsFile = RulesFile.Load(root, WordRules.RelativePath);

        var placement = PlacementRules.Read(placementFile);
        var comments = CommentRules.Read(commentsFile);
        var words = WordRules.Read(wordsFile);

        return new(
            placement,
            comments,
            words,
            [.. placementFile.Breaches, .. commentsFile.Breaches, .. wordsFile.Breaches]);
    }
}

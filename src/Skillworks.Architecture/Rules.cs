using Skillworks.Architecture.Comments;
using Skillworks.Architecture.Contexts;
using Skillworks.Architecture.Determinism;
using Skillworks.Architecture.Placement;
using Skillworks.Architecture.RulesFiles;
using Skillworks.Architecture.Words;

namespace Skillworks.Architecture;

internal sealed record Rules(
    PlacementRules Placement,
    CommentRules Comments,
    WordRules Words,
    ContextRules Contexts,
    DeterminismRules Determinism,
    IReadOnlyList<Breach> Breaches)
{
    public static Rules Read(string root)
    {
        var placementFile = RulesFile.Load(root, PlacementRules.RelativePath);
        var commentsFile = RulesFile.Load(root, CommentRules.RelativePath);
        var wordsFile = RulesFile.Load(root, WordRules.RelativePath);
        var contextsFile = RulesFile.Load(root, ContextRules.RelativePath);
        var determinismFile = RulesFile.Load(root, DeterminismRules.RelativePath);

        var placement = PlacementRules.Read(placementFile);
        var comments = CommentRules.Read(commentsFile);
        var words = WordRules.Read(wordsFile);
        var contexts = ContextRules.Read(contextsFile);
        var determinism = DeterminismRules.Read(determinismFile);

        return new(
            placement,
            comments,
            words,
            contexts,
            determinism,
            [
                .. placementFile.Breaches,
                .. commentsFile.Breaches,
                .. wordsFile.Breaches,
                .. contextsFile.Breaches,
                .. determinismFile.Breaches,
            ]);
    }
}

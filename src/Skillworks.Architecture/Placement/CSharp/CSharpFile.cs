using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;

namespace Skillworks.Architecture.Placement.CSharp;

internal sealed class CSharpFile
{
    private CSharpFile(CompilationUnitSyntax unit)
    {
        var types = unit
            .DescendantNodes()
            .OfType<MemberDeclarationSyntax>()
            .Where(declaration => declaration is BaseTypeDeclarationSyntax or DelegateDeclarationSyntax)
            .Where(declaration => !declaration.IsKind(SyntaxKind.ExtensionBlockDeclaration))
            .ToList();

        TopLevelTypes = [.. types.Where(type => type.Parent is not TypeDeclarationSyntax).Select(Declared)];
        NestedTypes = [.. types.Where(type => type.Parent is TypeDeclarationSyntax).Select(Declared)];
        HasTopLevelStatements = unit.Members.OfType<GlobalStatementSyntax>().Any();

        // An alias and a static using carry the name they reach in the same place as a plain one.
        Usings =
        [
            .. unit
                .DescendantNodes()
                .OfType<UsingDirectiveSyntax>()
                .Select(directive => directive.Name?.ToString())
                .OfType<string>(),
        ];
    }

    public IReadOnlyList<DeclaredType> TopLevelTypes { get; }

    public IReadOnlyList<DeclaredType> NestedTypes { get; }

    public bool HasTopLevelStatements { get; }

    public IReadOnlyList<string> Usings { get; }

    public static bool IsCSharp(string file) => Path.GetExtension(file) == ".cs";

    public static CSharpFile Read(string root, string file) =>
        new(CSharpSyntaxTree.ParseText(File.ReadAllText(Path.Combine(root, file))).GetCompilationUnitRoot());

    private static DeclaredType Declared(MemberDeclarationSyntax type)
    {
        (string name, TypeParameterListSyntax? parameters) = type switch
        {
            TypeDeclarationSyntax declaration => (declaration.Identifier.Text, declaration.TypeParameterList),
            DelegateDeclarationSyntax declaration => (declaration.Identifier.Text, declaration.TypeParameterList),
            BaseTypeDeclarationSyntax declaration => (declaration.Identifier.Text, null),
            _ => throw new ArgumentOutOfRangeException(nameof(type)),
        };

        var modifiers = type.Modifiers;

        return new DeclaredType(
            name,
            parameters?.Parameters.Count ?? 0,
            string.Join('.', type.Ancestors().OfType<BaseNamespaceDeclarationSyntax>().Reverse().Select(space => space.Name.ToString())),
            modifiers.Any(SyntaxKind.PartialKeyword),
            modifiers.Any(SyntaxKind.FileKeyword)
            || modifiers.Any(SyntaxKind.PrivateKeyword) && !modifiers.Any(SyntaxKind.ProtectedKeyword)
            || type.Parent is ClassDeclarationSyntax or StructDeclarationSyntax or RecordDeclarationSyntax
                && !modifiers.Any(IsAccessWord));
    }

    private static bool IsAccessWord(SyntaxToken modifier) =>
        modifier.Kind() is SyntaxKind.PublicKeyword or SyntaxKind.InternalKeyword
            or SyntaxKind.ProtectedKeyword or SyntaxKind.PrivateKeyword;
}

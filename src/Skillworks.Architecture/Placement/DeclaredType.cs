namespace Skillworks.Architecture.Placement;

internal sealed record DeclaredType(string Name, int Arity, string Namespace, bool IsPartial, bool IsHidden)
{
    public override string ToString() => Arity == 0 ? Name : $"{Name}<{new string(',', Arity - 1)}>";
}

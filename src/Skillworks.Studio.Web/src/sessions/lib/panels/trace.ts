import type { Depth } from './agents';

export interface TracePage {
  kind: 'trace';
  // Step ids alone, as the browser is sent a Session and never a Span.
  inside: Record<string, string>;
}

// A flat row with how far in it sits, so the panel draws the tree without a list inside a list.
export interface Node<T> {
  mark: T;
  level: number;
}

interface Placed {
  step: { id: string };
  startMs: number;
}

export function treeOf<T extends Placed>(marks: readonly T[], inside: Record<string, string>): Node<T>[] {
  const order = marks.toSorted((one, other) => one.startMs - other.startMs);
  const held = new Set(order.map((mark) => mark.step.id));
  const beneath = new Map<string, T[]>();
  const roots: T[] = [];

  for (const mark of order) {
    const outer = inside[mark.step.id];

    // A Step whose outer Step is out of view sits at the root, so nothing in view is hidden.
    if (outer !== undefined && outer !== mark.step.id && held.has(outer)) {
      const kin = beneath.get(outer);

      if (kin === undefined) {
        beneath.set(outer, [mark]);
      } else {
        kin.push(mark);
      }
    } else {
      roots.push(mark);
    }
  }

  const rows: Node<T>[] = [];
  const drawn = new Set<string>();

  const draw = (mark: T, level: number) => {
    if (drawn.has(mark.step.id)) {
      return;
    }

    drawn.add(mark.step.id);
    rows.push({ mark, level });

    for (const inner of beneath.get(mark.step.id) ?? []) {
      draw(inner, level + 1);
    }
  };

  roots.forEach((root) => draw(root, 0));
  // Steps that ring round each other reach no root, and one nobody can see is worse than one at the root.
  order.forEach((mark) => draw(mark, 0));

  return rows;
}

export function deepestOf<T>(rows: readonly Node<T>[]): number {
  return rows.reduce((deepest, row) => Math.max(deepest, row.level + 1), 0);
}

// A Thin run has no Span to nest by, so it says so rather than reading as a run that nested nothing.
export function noTreeWord(depth: Depth): string {
  return depth === 'thin' ? 'A thin run cannot say what ran inside what.' : 'Nothing ran in view.';
}

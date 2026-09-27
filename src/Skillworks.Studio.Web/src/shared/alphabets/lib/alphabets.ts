export type Alphabet = 'identity' | 'condition' | 'cause';

export interface SymbolTable {
  alphabet: Alphabet;
  glyphs: readonly string[];
}

export interface Crossing {
  glyph: string;
  tables: string[];
}

// Reuse inside one alphabet is wanted, so only a symbol that changes meaning is reported.
export function crossings(tables: Readonly<Record<string, SymbolTable>>): Crossing[] {
  const homes = new Map<string, { alphabets: Set<Alphabet>; tables: string[] }>();

  for (const [name, table] of Object.entries(tables)) {
    for (const glyph of table.glyphs) {
      const home = homes.get(glyph) ?? { alphabets: new Set<Alphabet>(), tables: [] };

      home.alphabets.add(table.alphabet);

      if (!home.tables.includes(name)) {
        home.tables.push(name);
      }

      homes.set(glyph, home);
    }
  }

  return [...homes]
    .filter(([, home]) => home.alphabets.size > 1)
    .map(([glyph, home]) => ({ glyph, tables: home.tables }));
}

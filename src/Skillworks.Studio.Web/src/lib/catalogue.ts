/**
 * The one rule the front end owns: how a catalogue location reads as a sentence. Structural, so
 * this module stays pure — it never imports the wire type that happens to match it.
 */
export function describeCatalogueLocation(location: { path: string; exists: boolean }): string {
  return location.exists
    ? `Catalogue found at ${location.path}`
    : `No catalogue at ${location.path}`;
}

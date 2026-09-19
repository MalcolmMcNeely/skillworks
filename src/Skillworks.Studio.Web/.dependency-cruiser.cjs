const { readFileSync } = require('node:fs');
const { join } = require('node:path');

// Any depth, so a Concern that nests, or a stray `src/lib`, is still held to the boundaries.
const layer = (names) => `^src/(.*/|)(${names})/`;

// The same list the architecture check reads, so adding a job is one line and never half a line.
const rulesFile = join(__dirname, '..', '..', '.claude', 'rules', 'file-placement.md');
const settings = readFileSync(rulesFile, 'utf8').match(/^```ya?ml[ \t]*\r?\n([\s\S]*?)^```/m)?.[1] ?? '';
const sliceNames = (settings.match(/^slices:[ \t]*\r?\n((?:[ \t]+-.*\r?\n)+)/m)?.[1] ?? '')
  .split('\n')
  .map((line) => line.replace(/^[ \t]*-[ \t]*/, '').trim())
  .filter(Boolean)
  .map((name) => name.toLowerCase());

// A list that came back empty would build a rule that matches nothing and pass everything in silence.
if (sliceNames.length === 0) {
  throw new Error(`Read no slices from ${rulesFile}. The Slice boundaries would hold nothing.`);
}

// A Slice only sits at the first level, so a deeper match would catch a folder that is not one.
const slice = `^src/(${sliceNames.join('|')})/`;
const shared = '^src/shared/';

// A test may read any Slice, because one that checks a seam has to see both sides of it.
const testFile = '\\.test\\.tsx?$';

/**
 * Module boundaries for the front end. The spec keeps this layer thin: `lib` is plain TypeScript
 * with tests beside it, `api` only fetches, `routes` only renders. Dependencies point downward.
 *
 * A `components` module may fetch. One that owns a write owns the read that follows it, and routing
 * that through a parent only spreads one concern over two files.
 * @type {import('dependency-cruiser').IConfiguration}
 */
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'A cycle means neither module can be understood on its own.',
      from: {},
      to: { circular: true },
    },
    {
      name: 'not-to-unresolvable',
      severity: 'error',
      comment: 'An import nothing resolves to is a typo or a missing dependency.',
      from: {},
      to: { couldNotResolve: true },
    },
    {
      name: 'slices-stay-apart',
      severity: 'error',
      comment:
        'A Slice holds one job of Studio. Reading another Slice makes the brief both jobs, so move ' +
        'the piece they share down into `shared`, or give this Slice one of its own.',
      from: { path: slice, pathNot: testFile },
      to: { path: slice, pathNot: '^src/$1/' },
    },
    {
      name: 'shared-stays-below',
      severity: 'error',
      comment:
        '`shared` never reads a Slice, so a Slice can be read in full without opening anything ' +
        'above it. Move the piece it needs down, or move this file up into the Slice it serves.',
      from: { path: shared, pathNot: testFile },
      to: { path: slice },
    },
    {
      name: 'lib-stays-pure',
      severity: 'error',
      comment: 'lib holds the calculation. It must not reach for the UI, the network or React.',
      from: { path: layer('lib') },
      to: { path: `${layer('api|routes')}|^node_modules/(react|react-dom|react-router)` },
    },
    {
      name: 'api-does-not-render',
      severity: 'error',
      comment: 'api fetches and nothing else.',
      from: { path: layer('api') },
      to: { path: layer('routes') },
    },
    {
      name: 'components-do-not-know-the-routes',
      severity: 'error',
      comment: 'A component is placed by a route, never the other way round.',
      from: { path: layer('components') },
      to: { path: layer('routes') },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    // Without this a type-only import is stripped before the graph is built, and `lib` could reach
    // up into `api` for a shape with the check still passing. The coupling is real either way.
    tsPreCompilationDeps: true,
    // Vite's own ambient types, referenced by a triple slash and resolved by nothing. There is no
    // boundary question in a file that declares no module of ours.
    exclude: { path: 'src/vite-env\\.d\\.ts$' },
    tsConfig: { fileName: 'tsconfig.app.json' },
    enhancedResolveOptions: {
      exportsFields: ['exports'],
      conditionNames: ['import', 'require', 'browser', 'default'],
      extensions: ['.js', '.jsx', '.ts', '.tsx'],
    },
  },
};

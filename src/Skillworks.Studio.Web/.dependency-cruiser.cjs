// Any depth, so a feature that nests, or a stray `src/lib`, is still held to the boundaries.
const layer = (names) => `^src/(.*/|)(${names})/`;

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

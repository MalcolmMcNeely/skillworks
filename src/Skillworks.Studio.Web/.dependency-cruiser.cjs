/**
 * Module boundaries for the front end. The spec keeps this layer thin: `lib` is plain TypeScript
 * with tests beside it, `api` only fetches, `routes` only renders. Dependencies point downward.
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
      from: { path: '^src/lib' },
      to: { path: '^(src/(api|routes)|node_modules/(react|react-dom|react-router))' },
    },
    {
      name: 'api-does-not-render',
      severity: 'error',
      comment: 'api fetches and nothing else.',
      from: { path: '^src/api' },
      to: { path: '^src/routes' },
    },
  ],
  options: {
    doNotFollow: { path: 'node_modules' },
    tsConfig: { fileName: 'tsconfig.app.json' },
    enhancedResolveOptions: {
      exportsFields: ['exports'],
      conditionNames: ['import', 'require', 'browser', 'default'],
      extensions: ['.js', '.jsx', '.ts', '.tsx'],
    },
  },
};

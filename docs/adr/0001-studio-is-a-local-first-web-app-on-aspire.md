# Studio is a local-first web app, C# behind React, run by Aspire

Studio has to author skills and run evals, and both write files and start `claude` on the machine
the developer is sitting at. A hosted service cannot do either, so Studio runs locally: an ASP.NET
Core API, a React front end served by Vite, and an Aspire AppHost that starts both with one F5.
`Skillworks.Core` holds the domain so the planned C# MCP server can be a second thin shell over it.

## Considered options

**A desktop shell** (Electron, Tauri, Photino) was rejected. The window is not what reaches the
filesystem, the server is, so the wrapper buys an icon and costs packaging, signing and updates.
The same React can be wrapped later without changing anything below it.

**A TypeScript backend** was rejected, and it is the closer call. The Claude Agent SDK ships for
Python and TypeScript only, so C# cannot use it. The documented alternative for every other
language is to run the CLI as a subprocess (`claude -p --output-format json`), and evals go through
`claude plugin eval`, which is a CLI command from any language. Against that, C# is the house
language, the MCP server is already planned in C# against the official
[MCP C# SDK](https://github.com/modelcontextprotocol/csharp-sdk), and one language covers both
shells. If a job later genuinely needs the Agent SDK, Aspire runs a Node service beside the C# one.

**No Aspire** was rejected. Aspire 13's `AddViteApp` runs `npm install` and `npm run dev` with hot
reload, injects the API address so no port is hard coded, and manages the telemetry containers
below. The alternative is two terminals, every day.

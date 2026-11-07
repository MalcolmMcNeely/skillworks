import type { EngineInterface, Register } from 'claude-code'

const PANE = 'loop-view'
const TITLE = 'Spec loops'
const POLL_MS = 3000

type TicketRow = { number: string; title: string; landed: boolean }

type TicketNow = {
  number: string
  title: string
  steps: string[]
  step: string | null
  step_started: string | null
}

type Position = {
  spec: string
  run: string
  doing: string
  tickets: TicketRow[]
  ticket: TicketNow | null
  at: number | null
  of: number | null
  seconds_left: number | null
  choices: number
  denials: number
  stop: { line: string; log: string } | null
}

// The driver writes "cutting" because the Position names what it does, and the pane says to what.
const DOING: Record<string, string> = { cutting: 'cutting tickets' }

function span(ms: number): string {
  const minutes = Math.floor(Math.max(0, ms) / 60000)
  if (minutes < 1) return `${Math.floor(Math.max(0, ms) / 1000)}s`
  if (minutes < 60) return `${minutes}m`
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

async function positions($: EngineInterface, root: string): Promise<Position[]> {
  if (!(await $.fs.exists(root))) return []
  const found: Position[] = []
  for (const entry of await $.fs.list(root)) {
    if (entry.kind !== 'dir') continue
    try {
      found.push(JSON.parse(String(await $.fs.read(`${root}/${entry.name}/position.json`))))
    } catch {
      // A spec folder from a run before the driver wrote a Position holds none, and shows no block.
    }
  }
  return found.sort((a, b) => Number(a.spec) - Number(b.spec))
}

function isLive(loop: Position): boolean {
  return loop.doing !== 'finished' && loop.doing !== 'stopped'
}

export const register: Register = on => {
  let loops: Position[] = []
  let now = 0
  const seen = new Set<string>()

  on('session.start', async ($, e, next) => {
    // The driver's own step Sessions load the Plugin headless, and a step must not pay for a pane.
    if (!e.isInteractive) return next(e)

    await $.command.register({ name: PANE, description: 'Open the pane that shows where each running loop is' })
    const root = `${e.cwd}/.spec-loop`
    const poll = async () => {
      loops = await positions($, root)
      now = await $.clock.now()
      const fresh = loops.filter(loop => isLive(loop) && !seen.has(loop.run))
      for (const loop of loops) seen.add(loop.run)
      // Only a run not seen before opens it, so a pane the developer closed stays closed.
      if (fresh.length > 0) void $.ui.open({ id: PANE, title: TITLE })
      $.ui.invalidate('ui.render')
    }
    await poll()
    $.clock.every(POLL_MS, () => void poll())
    return next(e)
  })

  on('command.run', { command: PANE }, async $ => {
    await $.ui.open({ id: PANE, title: TITLE })
    return { text: 'The loop pane is open.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    return (
      <Box flexDirection="column">
        {loops.length === 0 && <Text dimColor>No loop has a Position in this clone.</Text>}
        {loops.map(loop => {
          const ticket = loop.ticket
          const stepAt = ticket?.step ? ticket.steps.indexOf(ticket.step) : -1
          const left = loop.seconds_left == null ? '' : `~${span(loop.seconds_left * 1000)} left · `
          return (
            <Box flexDirection="column">
              <Text bold>Spec #{loop.spec} · {DOING[loop.doing] ?? loop.doing}</Text>
              <Text dimColor>{left}{loop.choices} Choices · {loop.denials} Denials</Text>
              {loop.stop && <Text color="red">{loop.stop.line}</Text>}
              {loop.stop && <Text>Log: {loop.stop.log}</Text>}
              {loop.tickets.map(row => (
                <Text color={row.landed ? 'green' : row.number === ticket?.number ? 'yellow' : undefined}>
                  {row.landed ? '✓' : row.number === ticket?.number ? '▶' : '·'} #{row.number} {row.title}
                </Text>
              ))}
              {ticket && <Text bold>#{ticket.number}, ticket {loop.at} of {loop.of}</Text>}
              {ticket?.steps.map((step, k) => (
                <Text color={k === stepAt ? 'yellow' : k < stepAt ? 'green' : undefined} dimColor={k > stepAt}>
                  {k < stepAt ? '✓' : k === stepAt ? '▶' : '○'} {step}
                  {k === stepAt && ticket.step_started ? `  ${span(now - Date.parse(ticket.step_started))} in step` : ''}
                </Text>
              ))}
            </Box>
          )
        })}
      </Box>
    )
  })
}

import type { EngineInterface, Register } from 'claude-code'

const PANE = 'loop-view'
const TITLE = 'Spec loops'
const POLL_MS = 3000
// The driver beats every 30 seconds, so four missed beats is a driver that died and not one that is slow.
const GONE_MS = 120_000
const CLEARED = 'cleared'
// The store holds every plugin's values in one file with a 4 MiB cap, so the oldest clears go first.
const CLEARS_KEPT = 500

type TicketRow = { number: string; title: string; landed: boolean; judge?: string | null }

type TicketNow = {
  number: string
  title: string
  steps: string[]
  step: string | null
  step_started: string | null
}

type Judge = { name: string; state: string; found: number | null; word?: string; filed: string[] }

type StepTime = { name: string; ticket: string | null; run: string; started: string; ended: string }

type Position = {
  spec: string
  run: string
  heartbeat: string
  doing: string
  judges?: Judge[]
  tickets: TicketRow[]
  ticket: TicketNow | null
  at: number | null
  of: number | null
  seconds_left: number | null
  choices: number
  denials: number
  stop: { line: string; log: string } | null
}

type Shown = { name: string; hint: string }

// The pane speaks to someone who has not read the docs, so each name is plain and each hint says what
// the step does. The driver's own names stay in the log and the Position.
const STEP: Record<string, Shown> = {
  build: { name: 'build', hint: 'Writes failing tests, then the code that passes them. Commits nothing.' },
  standards: {
    name: 'review: standards',
    hint: 'Reviews the change against your rules. Fixes what it can, and reports the rest.',
  },
  spec: {
    name: 'review: spec',
    hint: 'Reviews the change against the ticket and the spec. Fixes what it can, and reports the rest.',
  },
  architecture: {
    name: 'review: architecture',
    hint: 'Reviews where the change sits and which way it points. Fixes what it can, and reports the rest.',
  },
  fix: {
    name: 'review fixes',
    hint: 'The build Session reads the three review reports and fixes what they left. Where two disagree, it picks one.',
  },
  sweep: {
    name: 'comment sweep',
    hint: 'Cuts each new comment that only repeats the code. Comments the change did not write stay.',
  },
  suite: { name: 'suite', hint: 'The script runs the checks in docs/skillworks/suite.json. No Session runs.' },
  finish: {
    name: 'close ticket and commit',
    hint: 'The build Session commits the change and closes the ticket. It does not push.',
  },
  land: {
    name: 'rebase, verify, and push',
    hint: 'The script rebases the ticket onto the newest Target branch, runs the Suite again, then pushes.',
  },
}

const GONE = 'gone'

const DOING: Record<string, Shown> = {
  cutting: { name: 'cutting tickets', hint: 'A Session splits the spec into tickets. This happens once per spec.' },
  'building tickets': {
    name: 'building tickets',
    hint: 'The loop takes each ticket through the same steps, one ticket at a time.',
  },
  'Deepening check': {
    name: 'the Deepening check',
    hint: 'A new Session looks for modules the spec left shallow. Each one it is sure of becomes a ticket.',
  },
  'Simplify check': {
    name: 'the Simplify check',
    hint: 'A new Session looks for code the spec made harder than it has to be. What it finds becomes one ticket.',
  },
  'drift check': {
    name: 'the drift check',
    hint: 'A new Session checks that the finished work does what the spec asked.',
  },
  'Name check': {
    name: 'the Name check',
    hint: 'A new Session checks the new names in the code against the glossary in CONTEXT.md.',
  },
  'full run': {
    name: 'the full run',
    hint: 'The script runs every check again on the newest Target branch. It ignores saved Proofs.',
  },
  finished: { name: 'finished', hint: 'Every ticket is on the Target branch.' },
  stopped: { name: 'stopped', hint: 'The loop ended early. The red line below says why. The log has the detail.' },
  [GONE]: { name: GONE, hint: 'The script quit before it wrote an end. Read loop.log for the last step it reached.' },
}

// A driver newer than the Plugin can write a name the pane has no words for, so it shows as written.
function shown(table: Record<string, Shown>, name: string): Shown {
  return table[name] ?? { name, hint: '' }
}

function count(n: number, one: string): string {
  return `${n} ${n === 1 ? one : `${one}s`}`
}

function span(ms: number): string {
  const minutes = Math.floor(Math.max(0, ms) / 60000)
  if (minutes < 1) return `${Math.floor(Math.max(0, ms) / 1000)}s`
  if (minutes < 60) return `${minutes}m`
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

const DONE = 'done'
const NOW = 'now'
const TO_COME = 'to come'
const OFF = 'off'

const JUDGE_SHORT: Record<string, string> = {
  'deepening-check': 'deepen',
  'simplify-check': 'simplify',
  'drift-check': 'drift',
  'name-check': 'names',
}

// The state colours green, yellow, red and gray stay off this list, so a tag never reads as a state.
const JUDGE_COLOR: Record<string, string> = {
  'deepening-check': 'magenta',
  'simplify-check': 'cyan',
  'drift-check': 'blue',
  'name-check': 'white',
}

const SPINNER = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
const MARK: Record<string, string> = { [DONE]: '✓', [TO_COME]: '○', [OFF]: '✕' }
const CHIP_COLOR: Record<string, string | undefined> = { [DONE]: 'green', [NOW]: 'yellow' }
const BAR_CELLS = 20

type Chip = { key: string; state: string; text: string }

type Path = { chips: Chip[]; value: number; max: number; text: string }

function isOwn(row: TicketRow): boolean {
  return !row.judge
}

// The total counts each judge once however many tickets it files, so a filing never moves the bar back.
function pathOf(loop: Position): Path {
  const own = loop.tickets.filter(isOwn)
  const ownLanded = own.filter(row => row.landed).length
  const landed = new Set(loop.tickets.filter(row => row.landed).map(row => row.number))
  const judges = loop.judges ?? []
  const on = judges.filter(judge => judge.state !== OFF)
  const judgePart = (judge: Judge) =>
    judge.state !== DONE ? 0
      : judge.filed.length === 0 ? 1
        : 0.5 + (0.5 * judge.filed.filter(number => landed.has(number)).length) / judge.filed.length
  const fullRun = loop.doing === 'finished' ? DONE : loop.doing === 'full run' ? NOW : TO_COME
  const ownState = own.length > 0 && ownLanded === own.length ? DONE
    : loop.doing === 'building tickets' || loop.doing === 'cutting' ? NOW : TO_COME

  const judgeText = (judge: Judge) => {
    const name = JUDGE_SHORT[judge.name] ?? judge.name
    if (judge.state !== DONE) return name
    const found = judge.found == null ? '' : ` · ${judge.found}${judge.word ? ` ${judge.word}` : ''}`
    const filed = judge.filed.length === 0 ? '' : ` → ${count(judge.filed.length, 'ticket')}`
    return `${name}${found}${filed}`
  }

  const value = ownLanded + on.reduce((sum, judge) => sum + judgePart(judge), 0) + (fullRun === DONE ? 1 : 0)
  const max = own.length + on.length + 1
  const percent = Math.floor((100 * value) / max)
  const ownText = `tickets ${ownLanded}/${own.length}`
  return {
    chips: [
      { key: 'tickets', state: ownState, text: ownText },
      ...judges.map(judge => ({ key: judge.name, state: judge.state, text: judgeText(judge) })),
      { key: 'full-run', state: fullRun, text: 'full run' },
    ],
    value,
    max,
    text: `${percent}% · ${ownText} · checks ${on.filter(judge => judge.state === DONE).length}/${on.length} · full run ${fullRun}`,
  }
}

function barOf(path: Path): string {
  const filled = Math.floor((BAR_CELLS * path.value) / path.max)
  return '█'.repeat(filled) + '░'.repeat(BAR_CELLS - filled)
}

// Turned by the Clock and not by a timer of its own, so a test that holds the Clock still holds the spinner.
function spinnerAt(now: number): string {
  return SPINNER.charAt(Math.floor(now / POLL_MS) % SPINNER.length)
}

type Loop = Position & { stepTimes: StepTime[] }

function stepTimesIn(text: string): StepTime[] {
  return text.split('\n').filter(line => line.trim()).map(line => JSON.parse(line))
}

async function loopsIn($: EngineInterface, root: string): Promise<Loop[]> {
  if (!(await $.fs.exists(root))) return []
  const found: Loop[] = []
  for (const entry of await $.fs.list(root)) {
    if (entry.kind !== 'dir') continue
    try {
      const position: Position = JSON.parse(String(await $.fs.read(`${root}/${entry.name}/position.json`)))
      const stepTimes = stepTimesIn(String(await $.fs.read(`${root}/${entry.name}/step-times.jsonl`)))
      if (Array.isArray(position.judges) && position.judges.length > 0 && stepTimes.length > 0) {
        found.push({ ...position, stepTimes })
      }
    } catch {
      // A spec folder missing either file is a run from before this pane, and shows no card.
    }
  }
  return found
}

// A run whose first piece has not ended yet started after every run that has one.
function startOfRun(loop: Loop): number {
  const own = loop.stepTimes.filter(piece => piece.run === loop.run).map(piece => Date.parse(piece.started))
  return own.length > 0 ? Math.min(...own) : Infinity
}

function lastEnd(loop: Loop): number {
  return Math.max(...loop.stepTimes.map(piece => Date.parse(piece.ended)))
}

function stacked(loops: Loop[], now: number): Loop[] {
  const bySpec = (a: Loop, b: Loop) => Number(a.spec) - Number(b.spec)
  const live = loops.filter(loop => !hasEnded(loop, now))
    .sort((a, b) => startOfRun(b) - startOfRun(a) || bySpec(a, b))
  const ended = loops.filter(loop => hasEnded(loop, now))
    .sort((a, b) => lastEnd(b) - lastEnd(a) || bySpec(a, b))
  return [...live, ...ended]
}

const BORDER: Record<string, string> = { running: 'yellow', finished: 'green', stopped: 'red', [GONE]: 'gray' }

function stateOf(loop: Position, now: number): string {
  if (isGone(loop, now)) return GONE
  return wroteItsEnd(loop) ? loop.doing : 'running'
}

function wroteItsEnd(loop: Position): boolean {
  return loop.doing === 'finished' || loop.doing === 'stopped'
}

function hasEnded(loop: Position, now: number): boolean {
  return wroteItsEnd(loop) || isGone(loop, now)
}

function isGone(loop: Position, now: number): boolean {
  return !wroteItsEnd(loop) && now - Date.parse(loop.heartbeat) > GONE_MS
}

async function clearsKept($: EngineInterface): Promise<string[]> {
  const kept = await $.store.get(CLEARED)
  return Array.isArray(kept) ? kept.filter((run): run is string => typeof run === 'string') : []
}

export const register: Register = on => {
  let loops: Loop[] = []
  let now = 0
  let cleared = new Set<string>()
  const seen = new Set<string>()

  on('session.start', async ($, e, next) => {
    // The driver's own step Sessions load the Plugin headless, and a step must not pay for a pane.
    if (!e.isInteractive) return next(e)

    await $.command.register({ name: PANE, description: 'Open the pane that shows where each running loop is' })
    cleared = new Set(await clearsKept($))
    const root = `${e.cwd}/.spec-loop`
    const poll = async () => {
      const found = (await loopsIn($, root)).filter(loop => !cleared.has(loop.run))
      now = await $.clock.now()
      loops = stacked(found, now)
      const fresh = loops.filter(loop => !hasEnded(loop, now) && !seen.has(loop.run))
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
    const { Box, Button, Text } = $.ui.resolve(e)
    const clear = async (run: string) => {
      cleared.add(run)
      loops = loops.filter(loop => loop.run !== run)
      $.ui.invalidate('ui.render')
      await $.store.set(CLEARED, [...cleared].slice(-CLEARS_KEPT))
    }
    const ticketRow = (loop: Loop, row: TicketRow) => {
      const isNow = row.number === loop.ticket?.number
      return (
        <Box key={`ticket-${loop.spec}-${row.number}`} flexDirection="row">
          <Text color={row.landed ? 'green' : isNow ? 'yellow' : undefined}>
            {row.landed ? '✓ Landed ' : isNow ? '▶ now    ' : '· to come'} #{row.number} {row.title}
          </Text>
          {row.judge ? (
            <Text color={JUDGE_COLOR[row.judge]}>  ◆ {JUDGE_SHORT[row.judge] ?? row.judge}</Text>
          ) : null}
        </Box>
      )
    }
    return (
      <Box flexDirection="column">
        {loops.length === 0 && <Text dimColor>No loop has a Position in this clone.</Text>}
        {loops.map(loop => {
          const ticket = loop.ticket
          const stepAt = ticket?.step ? ticket.steps.indexOf(ticket.step) : -1
          const doing = shown(DOING, isGone(loop, now) ? GONE : loop.doing)
          const left = loop.seconds_left == null ? '' : `~${span(loop.seconds_left * 1000)} left · `
          const path = hasEnded(loop, now) ? null : pathOf(loop)
          const hint = ticket?.step ? shown(STEP, ticket.step).hint : ''
          return (
            <Box key={`card-${loop.spec}`} flexDirection="column" borderStyle="round"
              borderColor={BORDER[stateOf(loop, now)]} paddingX={1}>
              <Text bold>Spec #{loop.spec} · {doing.name}</Text>
              {!ticket && doing.hint && <Text dimColor>{doing.hint}</Text>}
              {path && (
                <Box key={`bar-${loop.spec}`}>
                  <Text color="yellow">{barOf(path)}</Text>
                </Box>
              )}
              {path && (
                <Box key={`bar-text-${loop.spec}`}>
                  <Text>{path.text}</Text>
                </Box>
              )}
              {path && (
                <Box flexDirection="row" flexWrap="wrap" columnGap={2}>
                  {path.chips.map(chip => (
                    <Box key={`chip-${loop.spec}-${chip.key}`}>
                      <Text color={CHIP_COLOR[chip.state]} dimColor={chip.state === TO_COME || chip.state === OFF}
                        strikethrough={chip.state === OFF}>
                        {chip.state === NOW ? spinnerAt(now) : MARK[chip.state] ?? MARK[TO_COME]} {chip.text}
                      </Text>
                    </Box>
                  ))}
                </Box>
              )}
              {path && ticket && <Text bold>Ticket {loop.at} of {loop.of}: #{ticket.number}</Text>}
              {path && ticket && (
                <Box flexDirection="row" flexWrap="wrap" columnGap={2}>
                  {ticket.steps.map((step, k) => {
                    const state = k < stepAt ? DONE : k === stepAt ? NOW : TO_COME
                    return (
                      <Box key={`step-${loop.spec}-${k}`}>
                        <Text color={CHIP_COLOR[state]} dimColor={state === TO_COME}>
                          {state === NOW ? spinnerAt(now) : MARK[state]} {shown(STEP, step).name}
                        </Text>
                      </Box>
                    )
                  })}
                </Box>
              )}
              {path && ticket?.step_started ? (
                <Text>{span(now - Date.parse(ticket.step_started))} in step</Text>
              ) : null}
              {path && hint ? (
                <Box marginLeft={2}>
                  <Text dimColor>{hint}</Text>
                </Box>
              ) : null}
              <Text dimColor>{left}{count(loop.choices, 'Choice')} · {count(loop.denials, 'Denial')}</Text>
              {hasEnded(loop, now) && (
                <Button key={`clear-${loop.run}`} label="Clear" onPress={() => clear(loop.run)} />
              )}
              {loop.stop && <Text color="red">{loop.stop.line}</Text>}
              {loop.stop && <Text>Log: {loop.stop.log}</Text>}
              {loop.tickets.filter(isOwn).map(row => ticketRow(loop, row))}
              {loop.tickets.some(row => !isOwn(row)) && (
                <Box key={`filed-${loop.spec}`}>
                  <Text bold>Filed by the checks</Text>
                </Box>
              )}
              {loop.tickets.filter(row => !isOwn(row)).map(row => ticketRow(loop, row))}
            </Box>
          )
        })}
      </Box>
    )
  })
}

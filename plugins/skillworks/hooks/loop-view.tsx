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

function hoursAndMinutes(ms: number): string {
  const minutes = Math.floor(Math.max(0, ms) / 60000)
  return minutes < 60 ? `${minutes}m` : `${Math.floor(minutes / 60)}h ${minutes % 60}m`
}

function span(ms: number): string {
  return ms < 60000 ? `${Math.floor(Math.max(0, ms) / 1000)}s` : hoursAndMinutes(ms)
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

function shortName(name: string): string {
  return JUDGE_SHORT[name] ?? name
}

function foundText(judge: Judge): string {
  return judge.found == null ? '' : ` · ${judge.found}${judge.word ? ` ${judge.word}` : ''}`
}

const JUDGE_LONG: Record<string, string> = {
  'deepening-check': shown(DOING, 'Deepening check').name,
  'simplify-check': shown(DOING, 'Simplify check').name,
  'drift-check': shown(DOING, 'drift check').name,
  'name-check': shown(DOING, 'Name check').name,
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
    const name = shortName(judge.name)
    if (judge.state !== DONE) return name
    const filed = judge.filed.length === 0 ? '' : ` → ${count(judge.filed.length, 'ticket')}`
    return `${name}${foundText(judge)}${filed}`
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

// The time a loop worked, so the hours it sat stopped between two starts do not count.
function timeTaken(loop: Loop): string {
  return hoursAndMinutes(loop.stepTimes.reduce((sum, piece) => sum + lengthOf(piece), 0))
}

// A developer reads the end against the clock on their own wall, so it is shown in the machine's zone.
function onTheWall(at: number): string {
  const when = new Date(at)
  return `${String(when.getHours()).padStart(2, '0')}:${String(when.getMinutes()).padStart(2, '0')}`
}

function headerOf(loop: Loop, state: string): string {
  const restarts = new Set(loop.stepTimes.map(piece => piece.run)).size - 1
  const restarted = restarts > 0 ? ` · restarted ${count(restarts, 'time')}` : ''
  return `Spec #${loop.spec} · ${state} · ${timeTaken(loop)} · ended ${onTheWall(lastEnd(loop))}${restarted}`
}

// A stop writes `stopped` over what the loop did, so a stop at a judge is read from the judge still marked now.
function pieceOf(loop: Position): string {
  const ticket = loop.ticket
  if (ticket) return `#${ticket.number}${ticket.step ? ` ${shown(STEP, ticket.step).name}` : ''}`
  const judge = (loop.judges ?? []).find(each => each.state === NOW)
  if (judge) return JUDGE_LONG[judge.name] ?? judge.name
  return shown(DOING, loop.doing).name
}

// A terminal names 15 colours that show on a dark background, one short of a run's 16 kinds, so the Cut takes a hex.
const KIND_COLOR: Record<string, string> = {
  ...JUDGE_COLOR,
  baseline: 'gray',
  cut: '#ff8700',
  build: 'green',
  standards: 'yellow',
  spec: 'yellowBright',
  architecture: 'red',
  fix: 'redBright',
  sweep: 'greenBright',
  suite: 'blueBright',
  finish: 'cyanBright',
  land: 'magentaBright',
  'full-run': 'whiteBright',
}
// A driver newer than the Plugin can write a kind with no colour here, so it borrows one.
const SPARE_COLORS = ['magenta', 'cyan', 'blue', 'white']
const TIME_CELLS = 40

function lengthOf(piece: StepTime): number {
  return Math.max(0, Date.parse(piece.ended) - Date.parse(piece.started))
}

// Rounding each part on its own can leave the shares at 99% or 101%, so the leftovers go to the largest remainders.
function splitInto(whole: number, amounts: number[]): number[] {
  const total = amounts.reduce((sum, amount) => sum + amount, 0)
  if (total === 0) return amounts.map(() => 0)
  const exact = amounts.map(amount => (whole * amount) / total)
  const short = whole - exact.reduce((sum, value) => sum + Math.floor(value), 0)
  const topped = new Set(exact.map((value, k) => ({ k, rest: value - Math.floor(value) }))
    .sort((a, b) => b.rest - a.rest || a.k - b.k)
    .slice(0, short)
    .map(({ k }) => k))
  return exact.map((value, k) => Math.floor(value) + (topped.has(k) ? 1 : 0))
}

type Kind = { name: string; shown: string; color: string; ms: number; share: number; cells: number }

function kindsOf(loop: Loop): Kind[] {
  const ms = new Map<string, number>()
  const inRunOrder = [...loop.stepTimes].sort((a, b) => Date.parse(a.started) - Date.parse(b.started))
  for (const piece of inRunOrder) ms.set(piece.name, (ms.get(piece.name) ?? 0) + lengthOf(piece))
  const amounts = [...ms.values()]
  const shares = splitInto(100, amounts)
  const cells = splitInto(TIME_CELLS, amounts)
  let spare = 0
  return [...ms.entries()].map(([name, time], k) => ({
    name,
    shown: shortName(name),
    color: KIND_COLOR[name] ?? SPARE_COLORS[spare++ % SPARE_COLORS.length] ?? 'white',
    ms: time,
    share: shares[k] ?? 0,
    cells: cells[k] ?? 0,
  }))
}

function longestOf(loop: Loop): string {
  const longest = loop.stepTimes.reduce((most, piece) => lengthOf(piece) > lengthOf(most) ? piece : most)
  return `Longest: ${longest.ticket ? `#${longest.ticket} ` : ''}${shortName(longest.name)}, ${span(lengthOf(longest))}`
}

function foundBy(judge: Judge): string {
  const name = shortName(judge.name)
  if (judge.state === OFF) return `${name} · off, did not run`
  if (judge.state === NOW) return `${name} · did not end`
  if (judge.state !== DONE) return `${name} · did not run`
  return `${name}${foundText(judge)} → ${count(judge.filed.length, 'ticket')}`
}

type Loop = Position & { folder: string; stepTimes: StepTime[] }

function stepTimesIn(text: string): StepTime[] {
  return text.split('\n').filter(line => line.trim()).map(line => JSON.parse(line))
}

async function stepTimesAt($: EngineInterface, path: string): Promise<StepTime[]> {
  try {
    return stepTimesIn(String(await $.fs.read(path)))
  } catch {
    return []
  }
}

// No judges means a run from before this pane; no Step times means still in the baseline, or ended with no summary.
async function loopsIn($: EngineInterface, root: string, now: number): Promise<Loop[]> {
  if (!(await $.fs.exists(root))) return []
  const found: Loop[] = []
  for (const entry of await $.fs.list(root)) {
    if (entry.kind !== 'dir') continue
    let position: Position
    try {
      position = JSON.parse(String(await $.fs.read(`${root}/${entry.name}/position.json`)))
    } catch {
      continue
    }
    if (!Array.isArray(position.judges) || position.judges.length === 0) continue
    const stepTimes = await stepTimesAt($, `${root}/${entry.name}/step-times.jsonl`)
    if (stepTimes.length === 0 && hasEnded(position, now)) continue
    found.push({ ...position, folder: entry.name, stepTimes })
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
      now = await $.clock.now()
      const found = (await loopsIn($, root, now)).filter(loop => !cleared.has(loop.run))
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
    const clear = async (...runs: string[]) => {
      for (const run of runs) cleared.add(run)
      loops = loops.filter(loop => !runs.includes(loop.run))
      $.ui.invalidate('ui.render')
      await $.store.set(CLEARED, [...cleared].slice(-CLEARS_KEPT))
    }
    // A stopped or gone loop still needs the developer, so one press never takes it off.
    const finished = loops.filter(loop => stateOf(loop, now) === 'finished')
    const ticketRow = (loop: Loop, row: TicketRow) => {
      const isNow = row.number === loop.ticket?.number
      return (
        <Box key={`ticket-${loop.spec}-${row.number}`} flexDirection="row">
          <Text color={row.landed ? 'green' : isNow ? 'yellow' : undefined}>
            {row.landed ? '✓ Landed ' : isNow ? '▶ now    ' : '· to come'} #{row.number} {row.title}
          </Text>
          {row.judge ? (
            <Text color={JUDGE_COLOR[row.judge]}>  ◆ {shortName(row.judge)}</Text>
          ) : null}
        </Box>
      )
    }
    return (
      <Box flexDirection="column">
        {loops.length === 0 && <Text dimColor>No loop has a Position in this clone.</Text>}
        {finished.length >= 2 && (
          <Button key="clear-all-finished" label={`Clear all finished (${finished.length})`}
            onPress={() => clear(...finished.map(loop => loop.run))} />
        )}
        {loops.map(loop => {
          if (hasEnded(loop, now)) {
            const state = stateOf(loop, now)
            const landed = loop.tickets.filter(row => row.landed).length
            const kinds = kindsOf(loop)
            return (
              <Box key={`card-${loop.spec}`} flexDirection="column" borderStyle="round"
                borderColor={BORDER[state]} paddingX={1}>
                <Text bold>{headerOf(loop, shown(DOING, state).name)}</Text>
                {loop.stop && <Text color="red">{loop.stop.line}</Text>}
                {state !== 'finished' && <Text>Log: {loop.stop?.log ?? `.spec-loop/${loop.folder}/loop.log`}</Text>}
                {state === 'stopped' && <Text>Stopped at {pieceOf(loop)}</Text>}
                {state === GONE && <Text>Last reached {pieceOf(loop)}</Text>}
                <Text dimColor>
                  {count(landed, 'ticket')} Landed · {count(loop.choices, 'Choice')} · {count(loop.denials, 'Denial')}
                </Text>
                {(loop.judges ?? []).map(judge => (
                  <Box key={`found-${loop.spec}-${judge.name}`}>
                    <Text color={JUDGE_COLOR[judge.name]}>{foundBy(judge)}</Text>
                  </Box>
                ))}
                <Text dimColor>Where the time went</Text>
                <Box key={`where-bar-${loop.spec}`} flexDirection="row">
                  {kinds.filter(kind => kind.cells > 0).map(kind => (
                    <Box key={`cells-${loop.spec}-${kind.name}`}>
                      <Text color={kind.color}>{'█'.repeat(kind.cells)}</Text>
                    </Box>
                  ))}
                </Box>
                {kinds.map(kind => (
                  <Box key={`share-${loop.spec}-${kind.name}`}>
                    <Text color={kind.color}>■ {kind.shown} · {kind.share}% · {span(kind.ms)}</Text>
                  </Box>
                ))}
                <Box key={`longest-${loop.spec}`}>
                  <Text bold>{longestOf(loop)}</Text>
                </Box>
                <Button key={`clear-${loop.run}`} label="Clear" onPress={() => clear(loop.run)} />
              </Box>
            )
          }
          const ticket = loop.ticket
          const stepAt = ticket?.step ? ticket.steps.indexOf(ticket.step) : -1
          const doing = shown(DOING, loop.doing)
          const left = loop.seconds_left == null ? '' : `~${span(loop.seconds_left * 1000)} left · `
          const path = pathOf(loop)
          const hint = ticket?.step ? shown(STEP, ticket.step).hint : ''
          return (
            <Box key={`card-${loop.spec}`} flexDirection="column" borderStyle="round"
              borderColor={BORDER[stateOf(loop, now)]} paddingX={1}>
              <Text bold>Spec #{loop.spec} · {doing.name}</Text>
              {!ticket && doing.hint && <Text dimColor>{doing.hint}</Text>}
              <Box key={`bar-${loop.spec}`}>
                <Text color="yellow">{barOf(path)}</Text>
              </Box>
              <Box key={`bar-text-${loop.spec}`}>
                <Text>{path.text}</Text>
              </Box>
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
              {ticket && <Text bold>Ticket {loop.at} of {loop.of}: #{ticket.number}</Text>}
              {ticket && (
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
              {ticket?.step_started ? (
                <Text>{span(now - Date.parse(ticket.step_started))} in step</Text>
              ) : null}
              {hint ? (
                <Box marginLeft={2}>
                  <Text dimColor>{hint}</Text>
                </Box>
              ) : null}
              <Text dimColor>{left}{count(loop.choices, 'Choice')} · {count(loop.denials, 'Denial')}</Text>
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

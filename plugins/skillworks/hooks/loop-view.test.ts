import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const CLONE = '/clone'
const NOW = Date.parse('2026-11-07T17:10:00Z')

const PANE = {
  plugin: 'skillworks',
  component: 'Pane',
  requestId: 'loop-view',
  props: {
    title: 'Spec loops',
    isFocused: false,
    bodyColumns: 60,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

type Position = Record<string, unknown>
type StepTime = { name: string; ticket: string | null; run: string; started: string; ended: string }

const JUDGES = ['deepening-check', 'simplify-check', 'drift-check', 'name-check'].map(name => ({
  name, state: 'to come', found: null, filed: [],
}))

function running(changes: Position = {}): Position {
  return {
    spec: '589',
    run: 'run-a',
    heartbeat: '2026-11-07T17:09:50Z',
    doing: 'building tickets',
    judges: JUDGES,
    tickets: [
      { number: '590', title: 'TICKET: The driver writes a Position', landed: true },
      { number: '592', title: 'TICKET: A pane shows every running loop', landed: false },
      { number: '593', title: 'TICKET: Clear a loop that ended', landed: false },
    ],
    ticket: {
      number: '592',
      title: 'TICKET: A pane shows every running loop',
      steps: ['build', 'standards', 'spec', 'land'],
      step: 'standards',
      step_started: '2026-11-07T17:06:00Z',
    },
    at: 2,
    of: 3,
    seconds_left: 3900,
    choices: 2,
    denials: 1,
    stop: null,
    ...changes,
  }
}

function baselineOf(position: Position, started = '2026-11-07T16:00:00Z', ended = '2026-11-07T16:02:00Z'): StepTime {
  return { name: 'baseline', ticket: null, run: String(position.run), started, ended }
}

// Claude Code spells the session's folder in the machine's own form, so a path is read by its parts.
function cloneHolding(on: On, positions: Record<string, Position>,
  stepTimes: Record<string, StepTime[] | null> = {}) {
  const reads: string[] = []
  const under = (path: string) => path.replace(/\\/g, '/').split('/.spec-loop')[1]
  const fileAt = (path: string) => {
    const [, folder = '', name = ''] = (under(path) ?? '').split('/')
    const position = positions[folder]
    if (position === undefined) return undefined
    if (name === 'position.json') return JSON.stringify(position)
    if (name !== 'step-times.jsonl') return undefined
    const kept = folder in stepTimes ? stepTimes[folder] : [baselineOf(position)]
    return kept?.map(entry => JSON.stringify(entry) + '\n').join('')
  }
  on('fs.exists', (_, e) => {
    reads.push(e.path)
    return { value: under(e.path) === '' && Object.keys(positions).length > 0 }
  })
  on('fs.list', (_, e) => {
    reads.push(e.path)
    return {
      value: Object.keys(positions).map(name => ({
        name, kind: 'dir' as const, size: 0, mtimeMs: 0, isLink: false,
      })),
    }
  })
  on('fs.read', (_, e) => {
    reads.push(e.path)
    const file = fileAt(e.path)
    if (file === undefined) throw new Error(`no file at ${e.path}`)
    return { value: file }
  })
  return { positions, reads }
}

function claudeCode(on: On, isInteractive = true) {
  const pane = { isOpen: false }
  mock.store(on)
  on('command.register', (_, e) => ({ value: { command: e.name } }))
  on('ui.open', () => {
    pane.isOpen = true
    return { value: { isPlaced: true } }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  return {
    pane,
    start: { cwd: CLONE, surface: isInteractive ? 'terminal' as const : null, isInteractive },
  }
}

// Claude Code closes the pane itself, and the mod hooks no close, so the pane just goes.
function closedByTheDeveloper(pane: { isOpen: boolean }) {
  pane.isOpen = false
}

async function lines($: Engine) {
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const texts = (await ui.findAll({ type: 'Text' })).map(text => text.text)
  await ui.unmount()
  return texts
}

const STOPPED = running({
  doing: 'stopped',
  stop: { line: 'STOP  #592 build        the build Session answered BLOCKED', log: '.spec-loop/589/loop.log' },
})

const FINISHED = running({
  doing: 'finished',
  tickets: [
    { number: '590', title: 'TICKET: The driver writes a Position', landed: true },
    { number: '592', title: 'TICKET: A pane shows every running loop', landed: true },
  ],
  ticket: null,
  at: null,
  of: null,
  seconds_left: null,
})

test('a stopped loop shows its stop line and the path to its log', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': STOPPED })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(await lines($)).toEqual(expect.arrayContaining([
    'Spec #589 · stopped',
    'STOP  #592 build        the build Session answered BLOCKED',
    'Log: .spec-loop/589/loop.log',
  ]))
})

test('a finished loop shows as finished, with no step', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': FINISHED })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(await lines($)).toEqual([
    'Spec #589 · finished',
    'Every ticket is on the Target branch.',
    '2 Choices · 1 Denial',
    '✓ Landed  #590 TICKET: The driver writes a Position',
    '✓ Landed  #592 TICKET: A pane shows every running loop',
  ])
})

test('two loops show as two cards, one for each spec', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running(), '600': running({ spec: '600', run: 'run-c', ticket: null, tickets: [] }) })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await lines($)).filter(line => line.startsWith('Spec #'))).toEqual([
    'Spec #589 · building tickets',
    'Spec #600 · building tickets',
  ])
})

test('a loop with a run the session has not seen opens the pane by itself', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running() })
  const { pane, start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(pane.isOpen).toBe(true)
})

test('a pane the developer closed stays closed while the run stays the same', async ($, on) => {
  // Arrange
  const clock = mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running() })
  const { pane, start } = claudeCode(on)
  await $.session.start(start)

  // Act
  closedByTheDeveloper(pane)
  await clock.advance(10_000)

  // Assert
  expect(pane.isOpen).toBe(false)
})

test('a new run opens a pane the developer closed', async ($, on) => {
  // Arrange
  const clock = mock.clock(on, { now: NOW })
  const { positions } = cloneHolding(on, { '589': running() })
  const { pane, start } = claudeCode(on)
  await $.session.start(start)
  closedByTheDeveloper(pane)

  // Act
  positions['589'] = running({ run: 'run-b' })
  await clock.advance(10_000)

  // Assert
  expect(pane.isOpen).toBe(true)
})

test('a loop that ended opens no pane by itself', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': FINISHED })
  const { pane, start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(pane.isOpen).toBe(false)
})

test('/loop-view opens the pane', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, {})
  const { pane, start } = claudeCode(on)
  await $.session.start(start)

  // Act
  await $.command.run({
    command: 'loop-view',
    args: '',
    origin: { kind: 'composer' },
    presentation: { isFullscreen: true, columns: 200 },
  })

  // Assert
  expect(pane.isOpen).toBe(true)
})

test('with no Position in the clone the mod opens no pane', async ($, on) => {
  // Arrange
  const clock = mock.clock(on, { now: NOW })
  cloneHolding(on, {})
  const { pane, start } = claudeCode(on)

  // Act
  await $.session.start(start)
  await clock.advance(10_000)

  // Assert
  expect(pane.isOpen).toBe(false)
})

test('in a headless session the mod reads nothing', async ($, on) => {
  // Arrange
  const clock = mock.clock(on, { now: NOW })
  const { reads } = cloneHolding(on, { '589': running() })
  const { start } = claudeCode(on, false)

  // Act
  await $.session.start(start)
  await clock.advance(10_000)

  // Assert
  expect(reads).toEqual([])
})

test('in a headless session the mod opens no pane', async ($, on) => {
  // Arrange
  const clock = mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running() })
  const { pane, start } = claudeCode(on, false)

  // Act
  await $.session.start(start)
  await clock.advance(10_000)

  // Assert
  expect(pane.isOpen).toBe(false)
})

test('a running loop whose heartbeat is older than 2 minutes shows as gone', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running({ heartbeat: '2026-11-07T17:07:59Z' }) })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await lines($))[0]).toBe('Spec #589 · gone')
})

test('a running loop whose heartbeat stops moving shows as gone once 2 minutes pass', async ($, on) => {
  // Arrange
  const clock = mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running() })
  const { start } = claudeCode(on)
  await $.session.start(start)

  // Act
  await clock.advance(120_000)

  // Assert
  expect((await lines($))[0]).toBe('Spec #589 · gone')
})

test('a running loop with a heartbeat under 2 minutes old shows as running', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running({ heartbeat: '2026-11-07T17:08:01Z' }) })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await lines($))[0]).toBe('Spec #589 · building tickets')
})

async function clearButtons($: Engine) {
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const found = await ui.findAll({ type: 'Button', text: 'Clear' })
  await ui.unmount()
  return found
}

async function clearedByTheDeveloper($: Engine) {
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const button = await ui.find({ type: 'Button', text: 'Clear' })
  await ui.press({ key: button?.key ?? '' })
  await ui.unmount()
}

const GONE = running({ heartbeat: '2026-11-07T17:07:59Z' })

test('a finished, a stopped and a gone loop each carry a Clear button', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, {
    '589': FINISHED,
    '600': { ...STOPPED, spec: '600', run: 'run-c' },
    '601': { ...GONE, spec: '601', run: 'run-d' },
  })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(await clearButtons($)).toHaveLength(3)
})

test('a running loop carries no Clear button', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running() })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(await clearButtons($)).toHaveLength(0)
})

test('a loop the developer cleared leaves the pane', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': STOPPED })
  const { start } = claudeCode(on)
  await $.session.start(start)

  // Act
  await clearedByTheDeveloper($)

  // Assert
  expect(await lines($)).toEqual(['No loop has a Position in this clone.'])
})

test('a cleared run stays out of the pane in a new Session', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': STOPPED })
  const { start } = claudeCode(on)
  await $.session.start(start)
  await clearedByTheDeveloper($)

  // Act
  await $.session.start(start)

  // Assert
  expect(await lines($)).toEqual(['No loop has a Position in this clone.'])
})

test('a new run of a cleared spec shows in the pane again', async ($, on) => {
  // Arrange
  const clock = mock.clock(on, { now: NOW })
  const { positions } = cloneHolding(on, { '589': STOPPED })
  const { start } = claudeCode(on)
  await $.session.start(start)
  await clearedByTheDeveloper($)

  // Act
  positions['589'] = running({ run: 'run-b' })
  await clock.advance(3_000)

  // Assert
  expect((await lines($))[0]).toBe('Spec #589 · building tickets')
})

test('a running ticket shows each step by its plain name, with a hint under the step it is on', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running() })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await lines($)).map(line => line.replace(SPINNER, '* '))).toEqual([
    'Spec #589 · building tickets',
    '██░░░░░░░░░░░░░░░░░░',
    '12% · tickets 1/3 · checks 0/4 · full run to come',
    '* tickets 1/3',
    '○ deepen',
    '○ simplify',
    '○ drift',
    '○ names',
    '○ full run',
    '~1h 5m left · 2 Choices · 1 Denial',
    '✓ Landed  #590 TICKET: The driver writes a Position',
    '▶ now     #592 TICKET: A pane shows every running loop',
    '· to come #593 TICKET: Clear a loop that ended',
    'Ticket 2 of 3: #592',
    '✓ build',
    '▶ review: standards  4m in step',
    'Reviews the change against your rules. Fixes what it can, and reports the rest.',
    '○ review: spec',
    '○ rebase, verify, and push',
  ])
})

test('a loop between tickets shows what it does now, with a hint', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running({ doing: 'drift check', ticket: null, at: null, of: null }) })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await lines($)).slice(0, 2)).toEqual([
    'Spec #589 · the drift check',
    'A new Session checks that the finished work does what the spec asked.',
  ])
})

test('a loop at the Deepening check shows its name and a hint', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running({ doing: 'Deepening check', ticket: null, at: null, of: null }) })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await lines($)).slice(0, 2)).toEqual([
    'Spec #589 · the Deepening check',
    'A new Session looks for modules the spec left shallow. Each one it is sure of becomes a ticket.',
  ])
})

test('a loop at the Simplify check shows its name and a hint', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running({ doing: 'Simplify check', ticket: null, at: null, of: null }) })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await lines($)).slice(0, 2)).toEqual([
    'Spec #589 · the Simplify check',
    'A new Session looks for code the spec made harder than it has to be. What it finds becomes one ticket.',
  ])
})

test('a step the pane has no name for shows as the driver names it, with no hint', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  const ticket = {
    number: '592',
    title: 'TICKET: A pane shows every running loop',
    steps: ['build', 'deploy'],
    step: 'deploy',
    step_started: '2026-11-07T17:06:00Z',
  }
  cloneHolding(on, { '589': running({ ticket }) })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  const shown = await lines($)
  expect(shown.slice(shown.indexOf('▶ deploy  4m in step'))).toEqual(['▶ deploy  4m in step'])
})

async function cards($: Engine) {
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const found = (await ui.findAll({ type: 'Box' }))
    .filter(box => box.key?.startsWith('card-'))
    .map(box => ({ spec: box.key?.slice('card-'.length), border: box.props.borderColor }))
  await ui.unmount()
  return found
}

test('each card has a border coloured by its state: running, finished, stopped or gone', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, {
    '589': running(),
    '600': { ...FINISHED, spec: '600', run: 'run-c' },
    '601': { ...STOPPED, spec: '601', run: 'run-d' },
    '602': { ...GONE, spec: '602', run: 'run-e' },
  })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(Object.fromEntries((await cards($)).map(card => [card.spec, card.border]))).toEqual({
    '589': 'yellow',
    '600': 'green',
    '601': 'red',
    '602': 'gray',
  })
})

test('running cards stack above ended cards, with the newest first in each group', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  const older = running({ spec: '589', run: 'run-a' })
  const newer = running({ spec: '590', run: 'run-b' })
  const endedFirst = { ...FINISHED, spec: '591', run: 'run-c' }
  const endedLast = { ...STOPPED, spec: '592', run: 'run-d' }
  cloneHolding(on, { '589': older, '590': newer, '591': endedFirst, '592': endedLast }, {
    '589': [baselineOf(older, '2026-11-07T15:00:00Z', '2026-11-07T15:02:00Z')],
    '590': [baselineOf(newer, '2026-11-07T16:30:00Z', '2026-11-07T16:32:00Z')],
    '591': [baselineOf(endedFirst, '2026-11-07T14:00:00Z', '2026-11-07T16:40:00Z')],
    '592': [baselineOf(endedLast, '2026-11-07T12:00:00Z', '2026-11-07T17:00:00Z')],
  })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await cards($)).map(card => card.spec)).toEqual(['590', '589', '592', '591'])
})

test('a loop folder whose Position has no judges shows no card', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  const { judges: _, ...before } = running()
  cloneHolding(on, { '589': before })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(await lines($)).toEqual(['No loop has a Position in this clone.'])
})

test('a loop folder with no Step times shows no card', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running() }, { '589': null })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(await lines($)).toEqual(['No loop has a Position in this clone.'])
})

const AT_THE_NAME_CHECK = running({
  doing: 'Name check',
  tickets: [
    { number: '590', title: 'TICKET: The driver writes a Position', landed: true, judge: null },
    { number: '592', title: 'TICKET: A pane shows every running loop', landed: true, judge: null },
    { number: '601', title: 'TICKET: Deepen the Position', landed: true, judge: 'deepening-check' },
    { number: '602', title: 'TICKET: Deepen the pane', landed: false, judge: 'deepening-check' },
  ],
  judges: [
    { name: 'deepening-check', state: 'done', found: 2, word: 'Strong', filed: ['601', '602'] },
    { name: 'simplify-check', state: 'off', found: null, word: 'findings', filed: [] },
    { name: 'drift-check', state: 'done', found: 0, word: 'Gaps', filed: [] },
    { name: 'name-check', state: 'now', found: null, word: 'renames', filed: [] },
  ],
  ticket: null,
  at: null,
  of: null,
})

// A Text carries no key, so each piece sits in a keyed Box and is read through it.
function shownIn(drawn: unknown): string {
  if (typeof drawn === 'string') return drawn
  if (Array.isArray(drawn)) return drawn.map(shownIn).join('')
  if (drawn && typeof drawn === 'object') {
    const element = drawn as { text?: unknown; children?: unknown }
    return typeof element.text === 'string' && element.text ? element.text : shownIn(element.children ?? [])
  }
  return ''
}

async function bar($: Engine) {
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const found = (await ui.findAll({ type: 'Box' }))
    .filter(box => box.key?.startsWith('bar-'))
    .map(shownIn)
  await ui.unmount()
  return found
}

async function pathRow($: Engine) {
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  const texts = await ui.findAll({ type: 'Text' })
  const found = (await ui.findAll({ type: 'Box' }))
    .filter(box => box.key?.startsWith('chip-'))
    .map(shownIn)
    .map(text => ({
      text,
      crossedOut: texts.find(drawn => drawn.text === text)?.props.strikethrough === true,
    }))
  await ui.unmount()
  return found
}

function percentOf(barText: string[]): number {
  return Number(/^(\d+)%/.exec(barText[1] ?? '')?.[1])
}

const SPINNER = /^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏] /

test('the bar counts each own ticket, each judge not off and the full run, with half a share for filing', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': AT_THE_NAME_CHECK })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(await bar($)).toEqual([
    '████████████░░░░░░░░',
    '62% · tickets 2/2 · checks 2/3 · full run to come',
  ])
})

test('the bar never moves back when a judge files a ticket', async ($, on) => {
  // Arrange
  const clock = mock.clock(on, { now: NOW })
  const judging = running({
    doing: 'Deepening check',
    ticket: null,
    tickets: [{ number: '590', title: 'TICKET: The driver writes a Position', landed: true, judge: null }],
    judges: JUDGES.map(judge => judge.name === 'deepening-check' ? { ...judge, state: 'now' } : judge),
  })
  const { positions } = cloneHolding(on, { '589': judging })
  const { start } = claudeCode(on)
  await $.session.start(start)
  const before = percentOf(await bar($))

  // Act
  positions['589'] = running({
    heartbeat: '2026-11-07T17:10:00Z',
    doing: 'building tickets',
    ticket: null,
    tickets: [
      { number: '590', title: 'TICKET: The driver writes a Position', landed: true, judge: null },
      { number: '601', title: 'TICKET: Deepen the Position', landed: false, judge: 'deepening-check' },
      { number: '602', title: 'TICKET: Deepen the pane', landed: false, judge: 'deepening-check' },
      { number: '603', title: 'TICKET: Deepen the driver', landed: false, judge: 'deepening-check' },
      { number: '604', title: 'TICKET: Deepen the Step times', landed: false, judge: 'deepening-check' },
    ],
    judges: JUDGES.map(judge => judge.name === 'deepening-check'
      ? { ...judge, state: 'done', found: 4, filed: ['601', '602', '603', '604'] } : judge),
  })
  await clock.advance(3_000)

  // Assert
  expect(percentOf(await bar($))).toBeGreaterThanOrEqual(before)
})

test('the path row shows the own tickets, each judge with its mark, and the full run', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': AT_THE_NAME_CHECK })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  const row = await pathRow($)
  expect(row.map(chip => chip.text.replace(SPINNER, '* '))).toEqual([
    '✓ tickets 2/2',
    '✓ deepen · 2 Strong → 2 tickets',
    '✕ simplify',
    '✓ drift · 0 Gaps',
    '* names',
    '○ full run',
  ])
})

test('an off judge is drawn crossed out in the path row', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': AT_THE_NAME_CHECK })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await pathRow($)).filter(chip => chip.crossedOut).map(chip => chip.text)).toEqual(['✕ simplify'])
})

test('the piece running now carries a spinner in the path row', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': AT_THE_NAME_CHECK })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await pathRow($)).filter(chip => SPINNER.test(chip.text)).map(chip => chip.text.slice(2)))
    .toEqual(['names'])
})

test('while tickets build, the own-tickets chip carries the spinner with Landed over total', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': running() })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect((await pathRow($))[0]?.text).toMatch(/^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏] tickets 1\/3$/)
})

test('an ended loop shows no bar and no path row', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': FINISHED })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect([...(await bar($)), ...(await pathRow($))]).toEqual([])
})

test('a single Choice and a single Denial read in the singular', async ($, on) => {
  // Arrange
  mock.clock(on, { now: NOW })
  cloneHolding(on, { '589': { ...FINISHED, choices: 1 } })
  const { start } = claudeCode(on)

  // Act
  await $.session.start(start)

  // Assert
  expect(await lines($)).toContain('1 Choice · 1 Denial')
})

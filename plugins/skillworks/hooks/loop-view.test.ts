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

function running(changes: Position = {}): Position {
  return {
    spec: '589',
    run: 'run-a',
    heartbeat: '2026-11-07T17:09:50Z',
    doing: 'building tickets',
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

// Claude Code spells the session's folder in the machine's own form, so a path is read by its parts.
function cloneHolding(on: On, positions: Record<string, Position>) {
  const reads: string[] = []
  const under = (path: string) => path.replace(/\\/g, '/').split('/.spec-loop')[1]
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
    const position = positions[(under(e.path) ?? '').split('/')[1] ?? '']
    if (position === undefined) throw new Error(`no file at ${e.path}`)
    return { value: JSON.stringify(position) }
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

test('two loops show as two blocks, one for each spec', async ($, on) => {
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
  expect(await lines($)).toEqual([
    'Spec #589 · building tickets',
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

import time
from datetime import timedelta

from clock.clock import Clock
from clock.held_clock import HeldClock


def test_the_real_clock_asks_the_machine_to_wait_the_time_it_is_given(monkeypatch):
    asked = []
    monkeypatch.setattr(time, "sleep", asked.append)

    Clock().wait(0.05)

    assert asked == [0.05]


def test_the_held_clock_moves_its_own_time_by_a_wait():
    clock = HeldClock()
    before = clock.now()

    clock.wait(0.05)

    assert clock.now() - before == timedelta(seconds=0.05)

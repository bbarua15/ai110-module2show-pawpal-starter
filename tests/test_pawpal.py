"""
Tests for PawPal+ core logic (pawpal_system.py).

Run with:
    pytest
or, from the project root:
    python -m pytest
"""

import sys
import os

# Allow tests/ to import pawpal_system.py from the project root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pawpal_system import Task, Pet, Owner, Scheduler


def test_task_mark_complete_changes_status():
    """Calling mark_complete() should flip a task's completed status to True."""
    task = Task(description="Morning walk", duration_minutes=20, priority="high")

    assert task.completed is False  # sanity check on the starting state

    task.mark_complete()

    assert task.completed is True


def test_adding_task_increases_pet_task_count():
    """Adding a task to a Pet should increase that pet's task count by one."""
    pet = Pet(name="Mochi", species="dog")

    assert len(pet.get_tasks()) == 0  # starts empty

    pet.add_task(Task(description="Feed breakfast", duration_minutes=10, priority="high"))

    assert len(pet.get_tasks()) == 1


def test_completing_daily_task_creates_next_occurrence():
    """Completing a daily task via the Scheduler should auto-create a fresh, incomplete copy."""
    pet = Pet(name="Mochi", species="dog")
    task = Task(description="Morning walk", duration_minutes=20, frequency="daily")
    pet.add_task(task)

    scheduler = Scheduler(available_minutes=60)
    next_task = scheduler.complete_task(pet, task)

    assert task.completed is True          # the original is marked done
    assert next_task is not None           # a new occurrence was returned
    assert next_task.completed is False    # the new occurrence starts fresh
    assert next_task is not task           # it's a distinct object, not the same one
    assert len(pet.get_tasks()) == 2       # the new occurrence was added to the pet


def test_completing_once_task_does_not_recur():
    """Completing a one-time task should NOT create a next occurrence."""
    pet = Pet(name="Mochi", species="dog")
    task = Task(description="Vet checkup", duration_minutes=30, frequency="once")
    pet.add_task(task)

    scheduler = Scheduler(available_minutes=60)
    next_task = scheduler.complete_task(pet, task)

    assert task.completed is True
    assert next_task is None
    assert len(pet.get_tasks()) == 1  # no new task was added


def test_next_occurrence_due_date_uses_timedelta_correctly():
    """Daily tasks should be due +1 day later; weekly tasks +7 days later."""
    from datetime import date

    pet = Pet(name="Mochi", species="dog")
    scheduler = Scheduler(available_minutes=60)

    daily = Task(description="Walk", duration_minutes=20, frequency="daily", due_date=date(2026, 1, 31))
    pet.add_task(daily)
    next_daily = scheduler.complete_task(pet, daily)
    assert next_daily.due_date == date(2026, 2, 1)  # correctly rolls over the month boundary

    weekly = Task(description="Grooming", duration_minutes=45, frequency="weekly", due_date=date(2026, 7, 7))
    pet.add_task(weekly)
    next_weekly = scheduler.complete_task(pet, weekly)
    assert next_weekly.due_date == date(2026, 7, 14)


def test_find_conflicts_detects_overlapping_tasks():
    """Two tasks whose time windows overlap should be reported as a conflict, even across pets."""
    from datetime import time

    mochi = Pet(name="Mochi", species="dog")
    whiskers = Pet(name="Whiskers", species="cat")

    task_a = Task(description="Morning walk", duration_minutes=20, start_time=time(8, 0))   # 8:00-8:20
    task_b = Task(description="Feed breakfast", duration_minutes=20, start_time=time(8, 10))  # 8:10-8:30
    mochi.add_task(task_a)
    whiskers.add_task(task_b)

    owner = Owner(name="Jordan")
    owner.add_pet(mochi)
    owner.add_pet(whiskers)

    scheduler = Scheduler(available_minutes=60)
    conflicts = scheduler.find_conflicts(owner.get_all_tasks())

    assert len(conflicts) == 1


def test_find_conflicts_ignores_adjacent_and_flexible_tasks():
    """Back-to-back tasks (no overlap) and tasks with no start_time should not be flagged."""
    from datetime import time

    pet = Pet(name="Mochi", species="dog")

    # 8:00-8:20, then 8:20-8:25 -- back-to-back, NOT overlapping (end == start is fine)
    back_to_back_a = Task(description="Morning walk", duration_minutes=20, start_time=time(8, 0))
    back_to_back_b = Task(description="Give medication", duration_minutes=5, start_time=time(8, 20))

    # No start_time at all -- flexible, should never conflict with anything
    flexible = Task(description="Play fetch", duration_minutes=30)

    pet.add_task(back_to_back_a)
    pet.add_task(back_to_back_b)
    pet.add_task(flexible)

    owner = Owner(name="Jordan")
    owner.add_pet(pet)

    scheduler = Scheduler(available_minutes=60)
    conflicts = scheduler.find_conflicts(owner.get_all_tasks())

    assert len(conflicts) == 0


def test_sort_by_time_returns_chronological_order():
    """sort_by_time() should return tasks ordered from shortest to longest duration."""
    tasks = [
        Task(description="Play fetch", duration_minutes=30),
        Task(description="Give medication", duration_minutes=5),
        Task(description="Morning walk", duration_minutes=20),
    ]

    scheduler = Scheduler(available_minutes=60)
    ordered = scheduler.sort_by_time(tasks)

    durations = [task.duration_minutes for task in ordered]
    assert durations == [5, 20, 30]


def test_check_conflicts_lightweight_flags_duplicate_times():
    """check_conflicts_lightweight() should warn when two tasks share the exact same start_time."""
    from datetime import time

    mochi = Pet(name="Mochi", species="dog")
    whiskers = Pet(name="Whiskers", species="cat")

    mochi.add_task(Task(description="Morning walk", duration_minutes=20, start_time=time(8, 0)))
    whiskers.add_task(Task(description="Feed breakfast", duration_minutes=10, start_time=time(8, 0)))

    owner = Owner(name="Jordan")
    owner.add_pet(mochi)
    owner.add_pet(whiskers)

    scheduler = Scheduler(available_minutes=60)
    warning = scheduler.check_conflicts_lightweight(owner.get_all_tasks())

    assert warning is not None
    assert "8" in warning  # sanity check that the warning mentions the shared hour
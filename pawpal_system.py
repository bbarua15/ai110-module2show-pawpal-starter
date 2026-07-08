"""
PawPal+ core system.

This module defines the domain model and scheduling logic for PawPal+.

Task, Pet, and Owner are implemented as dataclasses since they are
primarily data holders (attributes + a couple of small helper methods).
Scheduler stays a plain class since its purpose is behavior, not state.
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple


# Priority ranking used for sorting: lower number = higher priority.
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass
class Task:
    """Represents a single pet care activity (walk, feeding, medication, etc.)."""

    description: str
    duration_minutes: int
    priority: str = "medium"          # "low" | "medium" | "high"
    frequency: str = "daily"          # "once" | "daily" | "weekly"
    completed: bool = False
    due_date: date = field(default_factory=date.today)
    start_time: Optional[time] = None  # clock time this task is scheduled for, if any

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.completed = True

    def mark_incomplete(self) -> None:
        """Reset this task to not completed (useful when a new day/period starts)."""
        self.completed = False

    def create_next_occurrence(self) -> Optional["Task"]:
        """Return a fresh, incomplete copy of this task due on its next date, or None if it doesn't recur."""
        if self.frequency == "daily":
            next_due = self.due_date + timedelta(days=1)
        elif self.frequency == "weekly":
            next_due = self.due_date + timedelta(weeks=1)
        else:
            return None
        return replace(self, completed=False, due_date=next_due)


@dataclass
class Pet:
    """Represents a single pet and stores its list of care tasks."""

    name: str
    species: str
    owner: Optional["Owner"] = None
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Add a new care task for this pet."""
        self.tasks.append(task)

    def get_tasks(self) -> List[Task]:
        """Return all tasks associated with this pet."""
        return list(self.tasks)


@dataclass
class Owner:
    """Represents the pet owner. Manages multiple pets and their tasks."""

    name: str
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a new pet under this owner."""
        pet.owner = self
        self.pets.append(pet)

    def get_all_tasks(self) -> List[Tuple[Pet, Task]]:
        """Return every task across every pet this owner manages, paired with its pet."""
        all_tasks: List[Tuple[Pet, Task]] = []
        for pet in self.pets:
            for task in pet.get_tasks():
                all_tasks.append((pet, task))
        return all_tasks


class Scheduler:
    """The "brain" of PawPal+: builds and explains a time-budgeted plan across an owner's pets."""

    def __init__(self, available_minutes: int):
        self.available_minutes: int = available_minutes

    def build_plan(self, owner: Owner) -> List[Tuple[Pet, Task]]:
        """Sort the owner's pending tasks by priority/duration and greedily fit them into the time budget."""
        pending = self._get_pending(owner.get_all_tasks())
        ordered = self._sort_tasks(pending)

        plan: List[Tuple[Pet, Task]] = []
        remaining_minutes = self.available_minutes

        for pet, task in ordered:
            if task.duration_minutes <= remaining_minutes:
                plan.append((pet, task))
                remaining_minutes -= task.duration_minutes

        return plan

    def explain(self, plan: List[Tuple[Pet, Task]]) -> str:
        """Return a human-readable explanation of the plan's ordering."""
        if not plan:
            return "No tasks were scheduled. Add some tasks or increase available time."

        lines = ["Today's plan:"]
        total_minutes = 0
        for i, (pet, task) in enumerate(plan, start=1):
            lines.append(
                f"  {i}. [{pet.name}] {task.description} "
                f"({task.duration_minutes} min, {task.priority} priority)"
            )
            total_minutes += task.duration_minutes

        lines.append(
            f"\nScheduled {len(plan)} task(s) using {total_minutes} of "
            f"{self.available_minutes} available minutes."
        )
        lines.append(
            "Tasks were chosen by priority first (high before medium before low), "
            "then by shortest duration, to fit as many important tasks as possible "
            "into the available time."
        )
        return "\n".join(lines)

    def complete_task(self, pet: Pet, task: Task) -> Optional[Task]:
        """Mark a task complete and automatically add its next occurrence to the pet, if it recurs."""
        task.mark_complete()
        next_task = task.create_next_occurrence()
        if next_task is not None:
            pet.add_task(next_task)
        return next_task

    def filter_tasks(
        self,
        tasks: List[Tuple[Pet, Task]],
        completed: Optional[bool] = None,
        pet_name: Optional[str] = None,
    ) -> List[Tuple[Pet, Task]]:
        """Return tasks matching the given completion status and/or pet name (both optional)."""
        result = tasks
        if completed is not None:
            result = [(pet, task) for pet, task in result if task.completed == completed]
        if pet_name is not None:
            result = [(pet, task) for pet, task in result if pet.name == pet_name]
        return result

    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Return the given Task objects sorted by duration (shortest first)."""
        return sorted(tasks, key=lambda task: task.duration_minutes)

    def check_conflicts_lightweight(self, tasks: List[Tuple[Pet, Task]]) -> Optional[str]:
        """
        Fast, crash-safe conflict check: groups tasks by exact start_time
        (O(n), not O(n^2)) and returns a warning string if any two tasks
        share a start time, or None if no conflicts are found.

        This is a lighter alternative to find_conflicts()/_windows_overlap():
        it only catches same-instant collisions, not partial time-window
        overlaps, but it's cheaper and defensively never raises -- any bad
        or missing data is reported as a warning instead of crashing the
        scheduling flow.
        """
        try:
            buckets: dict = {}
            for pet, task in tasks:
                start = getattr(task, "start_time", None)
                if start is None:
                    continue  # flexible tasks can't conflict
                buckets.setdefault(start, []).append((pet, task))

            warnings = []
            for start, entries in buckets.items():
                if len(entries) > 1:
                    names = ", ".join(f"[{pet.name}] {task.description}" for pet, task in entries)
                    warnings.append(f"{len(entries)} tasks scheduled at {start}: {names}")

            if not warnings:
                return None
            return "Warning - possible scheduling conflicts:\n  " + "\n  ".join(warnings)

        except Exception as exc:
            # Never let a conflict check crash the app -- degrade to a warning.
            return f"Warning - could not fully check for conflicts ({exc})."

    def find_conflicts(
        self, tasks: List[Tuple[Pet, Task]]
    ) -> List[Tuple[Tuple[Pet, Task], Tuple[Pet, Task]]]:
        """Return pairs of (pet, task) entries whose scheduled time windows overlap."""
        # Only tasks with an explicit start_time can conflict; flexible
        # (unscheduled) tasks have no fixed slot to collide with.
        timed = [(pet, task) for pet, task in tasks if task.start_time is not None]

        conflicts: List[Tuple[Tuple[Pet, Task], Tuple[Pet, Task]]] = []
        for i in range(len(timed)):
            for j in range(i + 1, len(timed)):
                if self._windows_overlap(timed[i][1], timed[j][1]):
                    conflicts.append((timed[i], timed[j]))
        return conflicts

    def _windows_overlap(self, task_a: Task, task_b: Task) -> bool:
        """Internal helper: check if two tasks' [start_time, start_time + duration) windows overlap."""
        start_a = datetime.combine(date.today(), task_a.start_time)
        end_a = start_a + timedelta(minutes=task_a.duration_minutes)
        start_b = datetime.combine(date.today(), task_b.start_time)
        end_b = start_b + timedelta(minutes=task_b.duration_minutes)
        return start_a < end_b and start_b < end_a

    def explain_conflicts(self, conflicts: List[Tuple[Tuple[Pet, Task], Tuple[Pet, Task]]]) -> str:
        """Return a human-readable summary of any scheduling conflicts found."""
        if not conflicts:
            return "No scheduling conflicts detected."

        lines = ["Scheduling conflicts detected:"]
        for (pet_a, task_a), (pet_b, task_b) in conflicts:
            lines.append(
                f"  - [{pet_a.name}] {task_a.description} ({task_a.start_time}) overlaps with "
                f"[{pet_b.name}] {task_b.description} ({task_b.start_time})"
            )
        return "\n".join(lines)

    def _sort_tasks(self, tasks: List[Tuple[Pet, Task]]) -> List[Tuple[Pet, Task]]:
        """Internal helper: order tasks by priority, then by duration (shortest first)."""
        return sorted(
            tasks,
            key=lambda pair: (
                _PRIORITY_ORDER.get(pair[1].priority, len(_PRIORITY_ORDER)),
                pair[1].duration_minutes,
            ),
        )

    def _get_pending(self, tasks: List[Tuple[Pet, Task]]) -> List[Tuple[Pet, Task]]:
        """Internal helper: filter out tasks already marked complete."""
        return [(pet, task) for pet, task in tasks if not task.completed]
    
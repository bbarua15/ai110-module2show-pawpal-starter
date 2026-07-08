"""
main.py — Temporary CLI testing ground for PawPal+ logic.

This script exists to verify that Task, Pet, Owner, and Scheduler work
correctly together BEFORE wiring anything into the Streamlit UI
(app.py). This is the "CLI-first" step in the workflow.
"""

from pawpal_system import Task, Pet, Owner, Scheduler


def main():
    # 1. Create an Owner
    owner = Owner("Jordan")

    # 2. Create at least two Pets
    mochi = Pet("Mochi", "dog")
    whiskers = Pet("Whiskers", "cat")

    owner.add_pet(mochi)
    owner.add_pet(whiskers)

    # 3. Add tasks DELIBERATELY OUT OF ORDER (not sorted by duration or
    # priority), to make sure sort_by_time() actually does something
    # rather than happening to match input order by coincidence.
    mochi.add_task(Task("Play fetch", duration_minutes=30, priority="low", frequency="once"))
    mochi.add_task(Task("Morning walk", duration_minutes=20, priority="high"))
    whiskers.add_task(Task("Clean litter box", duration_minutes=15, priority="medium"))
    mochi.add_task(Task("Give medication", duration_minutes=5, priority="high"))  # frequency="daily" (default)
    whiskers.add_task(Task("Feed breakfast", duration_minutes=10, priority="high"))

    # Mark one non-recurring task complete so the completion filter has
    # something to exclude, without it spawning a recurrence.
    mochi.tasks[0].mark_complete()  # "Play fetch" (frequency="once", so no recurrence)

    scheduler = Scheduler(available_minutes=45)

    # Mark one task complete via the Scheduler (not task.mark_complete()
    # directly) so we exercise the automatic recurrence logic: completing
    # a "daily"/"weekly" task should spawn a fresh incomplete copy of it.
    recurring_task = mochi.tasks[2]  # "Give medication" (frequency defaults to "daily")
    print(f"=== Completing '{recurring_task.description}' (frequency={recurring_task.frequency}) ===")
    next_occurrence = scheduler.complete_task(mochi, recurring_task)
    if next_occurrence:
        print(f"  -> Next occurrence auto-created: '{next_occurrence.description}' "
              f"(completed={next_occurrence.completed})")
    else:
        print("  -> No next occurrence created (task does not recur).")
    print(f"  Mochi now has {len(mochi.get_tasks())} tasks.\n")

    all_tasks = owner.get_all_tasks()  # list of (Pet, Task) tuples

    # ------------------------------------------------------------------
    # Demonstrate sort_by_time()
    # ------------------------------------------------------------------
    print("=== All tasks, unsorted (input order) ===")
    for pet, task in all_tasks:
        print(f"  [{pet.name}] {task.description} - {task.duration_minutes} min")

    print("\n=== All tasks, sorted by time (shortest first) ===")
    just_tasks = [task for _, task in all_tasks]
    for task in scheduler.sort_by_time(just_tasks):
        print(f"  {task.description} - {task.duration_minutes} min")

    # ------------------------------------------------------------------
    # Demonstrate filter_tasks()
    # ------------------------------------------------------------------
    print("\n=== Filter: incomplete tasks only ===")
    for pet, task in scheduler.filter_tasks(all_tasks, completed=False):
        print(f"  [{pet.name}] {task.description}")

    print("\n=== Filter: completed tasks only ===")
    for pet, task in scheduler.filter_tasks(all_tasks, completed=True):
        print(f"  [{pet.name}] {task.description}")

    print("\n=== Filter: Mochi's tasks only ===")
    for pet, task in scheduler.filter_tasks(all_tasks, pet_name="Mochi"):
        print(f"  [{pet.name}] {task.description}")

    print("\n=== Filter: Mochi's incomplete tasks only (combined filter) ===")
    for pet, task in scheduler.filter_tasks(all_tasks, completed=False, pet_name="Mochi"):
        print(f"  [{pet.name}] {task.description}")

    # ------------------------------------------------------------------
    # Build and print today's schedule (unaffected by the above; uses
    # its own internal priority+duration sort and pending-task filter)
    # ------------------------------------------------------------------
    print("\n=== Today's Schedule ===")
    plan = scheduler.build_plan(owner)
    print(scheduler.explain(plan))


if __name__ == "__main__":
    main()

    
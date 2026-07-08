# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

PawPal+ is built around three core actions a user should be able to perform:

1. **Add a pet and its care tasks** — The owner can register a pet and add
   individual care tasks for it (e.g., a walk, a feeding, a medication dose,
   or a vet appointment), specifying at minimum a duration and a priority
   level for each.
2. **Generate today's schedule** — Given the current list of tasks and any
   time constraints (like total available minutes in the day), the system
   builds an ordered daily plan, deciding which tasks to include and in what
   sequence.
3. **View today's plan** — The owner can view the generated schedule for the
   day, along with a short explanation of why tasks were ordered or
   prioritized the way they were.

My initial UML design centers on four classes: `Owner`, `Pet`, `Task`, and
`Scheduler`.

- **Owner** represents the person using the app. It holds the owner's name
  and a list of `Pet` objects they manage, with a single responsibility:
  registering new pets (`add_pet`).

- **Pet** represents an individual animal and is the container for that
  pet's care tasks. It holds a name, species, a reference back to its
  owner, and a list of `Task` objects. Its responsibility is limited to
  managing that list — adding tasks and returning them (`add_task`,
  `get_tasks`) — it doesn't make any scheduling decisions itself.

- **Task** is the core unit of care the whole system operates on — a walk,
  a feeding, a medication dose, etc. It holds a title, duration, priority,
  category, and completion status. It's intentionally a thin data object;
  its only behavior is marking itself complete (`mark_complete`).

- **Scheduler** is where all the decision-making lives. It takes a pet's
  tasks plus a time constraint (`available_minutes`) and is responsible for
  building an ordered daily plan (`build_plan`) and explaining the
  reasoning behind it (`explain`). Internally it also handles sorting
  tasks by priority/duration and filtering out completed ones.


**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.

**b. Design changes**

Yes — my design changed twice before I started implementing any logic.

1. **Dropped a separate `Plan` class.** My first draft had five classes:
   `Owner`, `Pet`, `Task`, `Scheduler`, and `Plan` (a dedicated object to
   hold the scheduling result). I merged `Plan` into `Scheduler`, having
   it return a plain list of ordered tasks and expose a separate
   `explain()` method instead. I made this change because "build a plan"
   and "explain a plan" are really two behaviors of the same scheduling
   step, not two separate entities — introducing a whole class just to
   hold a list and a string felt like unnecessary structure for what the
   project actually required.

2. **Removed features that weren't tied to a core action.** My first UML
   pass included a `fixed_time` attribute and `is_fixed()` method on
   `Task`, a `resolve_conflicts()` method on `Scheduler`, and a
   `preferences` dict on `Owner`. None of these were needed to support
   the three core actions (add pet/task, generate a plan, view the plan)
   — they were speculative additions for features I hadn't actually
   designed yet, like appointment-anchored scheduling. I removed them to
   keep the first working version focused, with the plan to add them back
   later only if a real use case demands it.

Both changes came from repeatedly checking each class/attribute/method
against the actual user actions the app needs to support, rather than
designing for hypothetical future features up front.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

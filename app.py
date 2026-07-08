import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.title("🐾 PawPal+")
st.caption("Smart pet care scheduling")

# ---------------------------------------------------------------------
# SESSION STATE SETUP
# Only create these objects the FIRST time the script runs for this
# session. On every rerun (button click, form submit, etc.), reuse what
# already exists instead of wiping it out.
# ---------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="")

if "pets" not in st.session_state:
    st.session_state.pets = {}  # maps pet name -> Pet object, for quick lookup


owner = st.session_state.owner

# ---------------------------------------------------------------------
# OWNER NAME
# ---------------------------------------------------------------------
owner_name = st.text_input("Your name", value=owner.name)
owner.name = owner_name  # cheap enough to just update directly each rerun

st.divider()

# ---------------------------------------------------------------------
# ADD A PET
# ---------------------------------------------------------------------
st.subheader("Add a Pet")

with st.form("add_pet_form"):
    pet_name = st.text_input("Pet name")
    species = st.selectbox("Species", ["Dog", "Cat", "Other"])
    submitted_pet = st.form_submit_button("Add Pet")

    if submitted_pet:
        if not pet_name:
            st.warning("Please enter a pet name.")
        elif pet_name in st.session_state.pets:
            st.warning(f"{pet_name} has already been added.")
        else:
            new_pet = Pet(name=pet_name, species=species)
            owner.add_pet(new_pet)
            st.session_state.pets[pet_name] = new_pet
            st.success(f"Added {pet_name} the {species.lower()}!")

if st.session_state.pets:
    st.write("**Current pets:**", ", ".join(st.session_state.pets.keys()))

st.divider()

# ---------------------------------------------------------------------
# ADD A TASK
# ---------------------------------------------------------------------
st.subheader("Schedule a Task")

if not st.session_state.pets:
    st.info("Add a pet first before scheduling tasks.")
else:
    with st.form("add_task_form"):
        selected_pet_name = st.selectbox("Pet", list(st.session_state.pets.keys()))
        description = st.text_input("Task description", placeholder="e.g. Morning walk")
        duration = st.number_input("Duration (minutes)", min_value=1, value=15, step=5)
        priority = st.selectbox("Priority", ["high", "medium", "low"])
        frequency = st.selectbox("Frequency", ["daily", "weekly", "once"])
        submitted_task = st.form_submit_button("Add Task")

        if submitted_task:
            if not description:
                st.warning("Please enter a task description.")
            else:
                target_pet = st.session_state.pets[selected_pet_name]
                new_task = Task(
                    description=description,
                    duration_minutes=int(duration),
                    priority=priority,
                    frequency=frequency,
                )
                target_pet.add_task(new_task)
                st.success(f"Added '{description}' for {selected_pet_name}.")

st.divider()

# ---------------------------------------------------------------------
# TASK CHECKLIST (mark tasks complete; recurring tasks auto-renew)
# ---------------------------------------------------------------------
st.subheader("Task Checklist")

all_tasks = owner.get_all_tasks() if st.session_state.pets else []
incomplete = [(pet, task) for pet, task in all_tasks if not task.completed]

if not incomplete:
    st.info("No pending tasks. Add a pet and a task above.")
else:
    # A lightweight Scheduler instance just to call complete_task(); the
    # available_minutes value here doesn't matter for this action.
    checklist_scheduler = Scheduler(available_minutes=0)

    for pet, task in incomplete:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"[{pet.name}] {task.description} ({task.duration_minutes} min, {task.frequency})")
        with col2:
            if st.button("Done", key=f"done_{id(task)}"):
                next_task = checklist_scheduler.complete_task(pet, task)
                if next_task is not None:
                    st.success(f"Completed! Next '{next_task.description}' scheduled for {next_task.frequency}.")
                else:
                    st.success("Completed!")
                st.rerun()

st.divider()

# ---------------------------------------------------------------------
# GENERATE SCHEDULE
# ---------------------------------------------------------------------
st.subheader("Today's Schedule")

available_minutes = st.slider("Available minutes today", 15, 240, 60, step=15)

if st.button("Generate schedule"):
    if not st.session_state.pets:
        st.warning("Add at least one pet and task before generating a schedule.")
    else:
        scheduler = Scheduler(available_minutes=available_minutes)
        plan = scheduler.build_plan(owner)
        st.text(scheduler.explain(plan))
        
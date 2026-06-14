from __future__ import annotations

import streamlit as st

from application.use_cases.create_project import create_project
from application.use_cases.inspect_checkpoints import inspect_checkpoints
from application.use_cases.inspect_context import inspect_context, inspect_report, inspect_trace
from application.use_cases.inspect_plot_threads import inspect_foreshadows, inspect_plot_threads
from application.use_cases.inspect_project import inspect_chapters, inspect_project, list_projects
from application.use_cases.run_chapter import run_chapter


st.set_page_config(page_title="Narrative Engine", layout="wide")
st.title("Narrative Engine Workbench")

projects = list_projects()
project_ids = [str(item.get("project_id")) for item in projects if item.get("project_id")]

with st.sidebar:
    st.header("Project")
    new_name = st.text_input("New project name", value="")
    if st.button("Create project") and new_name.strip():
        create_project(new_name.strip())
        st.rerun()
    project_id = st.selectbox("project_id", project_ids) if project_ids else ""
    chapter_id = st.number_input("chapter_id", min_value=1, value=1, step=1)
    if project_id and st.button("Run chapter pipeline"):
        st.json(run_chapter(project_id, int(chapter_id)))

if not project_id:
    st.info("Create or select a project.")
    st.stop()

overview = inspect_project(project_id)
snapshot = overview["snapshot"]
chapters = inspect_chapters(project_id)

tabs = st.tabs(
    [
        "Overview",
        "Chapters",
        "Story Bible",
        "Characters",
        "Locations",
        "Organizations",
        "Plot Threads",
        "Foreshadows",
        "Context Audit",
        "Pipeline Trace",
        "Consistency Report",
        "Checkpoints",
    ]
)

with tabs[0]:
    st.json(overview["project"])
    st.metric("Current chapter", snapshot.get("current_chapter", 0))

with tabs[1]:
    st.dataframe(chapters)

with tabs[2]:
    st.json(snapshot.get("story_bible", {}))

with tabs[3]:
    st.dataframe(snapshot.get("characters", []))

with tabs[4]:
    st.dataframe(snapshot.get("locations", []))

with tabs[5]:
    st.dataframe(snapshot.get("organizations", []))

with tabs[6]:
    st.dataframe(inspect_plot_threads(project_id))

with tabs[7]:
    st.dataframe(inspect_foreshadows(project_id))

with tabs[8]:
    try:
        st.json(inspect_context(project_id, int(chapter_id)))
    except Exception as exc:
        st.warning(str(exc))

with tabs[9]:
    try:
        st.json(inspect_trace(project_id, int(chapter_id)))
    except Exception as exc:
        st.warning(str(exc))

with tabs[10]:
    try:
        st.json(inspect_report(project_id, int(chapter_id)))
    except Exception as exc:
        st.warning(str(exc))

with tabs[11]:
    st.json(inspect_checkpoints(project_id))

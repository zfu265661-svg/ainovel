from domain.models.narrative_snapshot import NarrativeSnapshot
from domain.models.project import NovelProject
from infrastructure.persistence.json_repository import JsonProjectRepository


def test_json_repository_saves_and_loads_project_and_snapshot(tmp_path):
    repo = JsonProjectRepository(tmp_path)
    repo.save_project(NovelProject(project_id="demo", name="Demo"))
    repo.save_snapshot(NarrativeSnapshot.empty("demo"))

    assert repo.load_project("demo").name == "Demo"
    assert repo.load_snapshot("demo").project_id == "demo"
    assert (tmp_path / "demo" / "project.json").is_file()
    assert (tmp_path / "demo" / "snapshot.json").is_file()

from domain.models import (
    Character,
    Checkpoint,
    ConsistencyFinding,
    ConsistencyReport,
    ContextPackage,
    NarrativeSnapshot,
    NovelProject,
    PipelineStageTrace,
    PipelineTrace,
)


def test_domain_models_serialize_to_json_dicts():
    project = NovelProject(project_id="demo", name="Demo")
    snapshot = NarrativeSnapshot.empty("demo")
    snapshot.characters.append(Character(id="c1", name="Alice").to_dict())
    context = ContextPackage(chapter_id=1, layers={"mandatory": [], "compressed": [], "recent": [], "optional": []})
    trace = PipelineTrace(project_id="demo", chapter_id=1, stages=[PipelineStageTrace(stage="prepare")])
    report = ConsistencyReport(project_id="demo", chapter_id=1, findings=[ConsistencyFinding("warning", "x", "msg")])
    checkpoint = Checkpoint(project_id="demo", chapter_id=1, checkpoint_id="cp1")

    assert project.to_dict()["project_id"] == "demo"
    assert snapshot.to_dict()["characters"][0]["name"] == "Alice"
    assert context.to_dict()["chapter_id"] == 1
    assert trace.to_dict()["stages"][0]["stage"] == "prepare"
    assert report.to_dict()["findings"][0]["level"] == "warning"
    assert checkpoint.to_dict()["checkpoint_id"] == "cp1"

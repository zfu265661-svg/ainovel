from domain.models.narrative_snapshot import NarrativeSnapshot
from engine.context.context_assembler import ContextAssembler


def test_context_assembler_outputs_four_layers_and_audit():
    snapshot = NarrativeSnapshot.empty("demo")
    snapshot.characters.append({"id": "c1", "name": "Alice", "current_state": "ready"})
    snapshot.locations.append({"id": "l1", "name": "Harbor"})
    snapshot.plot_threads.append({"id": "t1", "title": "Mystery", "status": "active"})
    snapshot.foreshadows.append({"id": "f1", "title": "Key", "status": "active"})
    snapshot.chapter_summaries.append({"chapter_id": 1, "summary": "Old", "handoff": "Next"})

    package = ContextAssembler().assemble(
        snapshot=snapshot,
        chapter_id=2,
        chapter_plan={"characters": ["Alice"], "locations": ["Harbor"]},
    )

    assert set(package.layers) == {"mandatory", "compressed", "recent", "optional"}
    assert "Alice" in package.audit.coverage["matched_entities"]
    assert "Harbor" in package.audit.coverage["matched_locations"]
    assert "t1" in package.audit.coverage["active_threads_included"]
    assert package.audit.budget["selected_items"] > 0

from __future__ import annotations

from typing import Any

from domain.models.context import ContextPackage
from domain.models.narrative_snapshot import NarrativeSnapshot
from engine.context.context_audit import build_context_audit
from engine.context.context_layers import context_item, empty_layers


class ContextAssembler:
    def __init__(self, max_items: int = 64) -> None:
        self.max_items = max_items

    def assemble(
        self,
        *,
        snapshot: NarrativeSnapshot,
        chapter_id: int,
        chapter_plan: dict[str, Any],
    ) -> ContextPackage:
        layers = empty_layers()
        warnings: list[str] = []

        plan_entities = self._plan_names(chapter_plan, "characters")
        plan_locations = self._plan_names(chapter_plan, "locations")
        plan_organizations = self._plan_names(chapter_plan, "organizations")

        matched_entities = self._match_items(snapshot.characters, plan_entities)
        matched_locations = self._match_items(snapshot.locations, plan_locations)
        matched_organizations = self._match_items(snapshot.organizations, plan_organizations)

        for item in matched_entities:
            layers["mandatory"].append(self._item("character", item, "chapter_plan"))
        for item in matched_locations:
            layers["mandatory"].append(self._item("location", item, "chapter_plan"))
        for item in matched_organizations:
            layers["mandatory"].append(self._item("organization", item, "chapter_plan"))

        previous_summary = self._previous_summary(snapshot, chapter_id)
        if previous_summary:
            if previous_summary.get("handoff"):
                layers["mandatory"].append(
                    context_item("handoff", f"ch{chapter_id - 1:03d}", "previous_handoff", "chapter_summary", previous_summary.get("handoff"))
                )
            else:
                warnings.append("previous_handoff_missing")
            layers["recent"].append(
                context_item("chapter_summary", f"ch{chapter_id - 1:03d}", "previous_summary", "chapter_summary", previous_summary)
            )
        elif chapter_id > 1:
            warnings.append("previous_summary_missing")

        active_threads = [item for item in snapshot.plot_threads if str(item.get("status")) in ("active", "unresolved")]
        dormant_threads = [item for item in snapshot.plot_threads if str(item.get("status")) == "dormant"]
        for item in active_threads:
            layers["mandatory"].append(self._item("plot_thread", item, "active_ledger"))
        for item in dormant_threads:
            layers["optional"].append(self._item("plot_thread", item, "dormant_ledger"))

        active_foreshadows = [item for item in snapshot.foreshadows if str(item.get("status")) == "active"]
        dormant_foreshadows = [item for item in snapshot.foreshadows if str(item.get("status")) == "dormant"]
        for item in active_foreshadows:
            layers["mandatory"].append(self._item("foreshadow", item, "active_ledger"))
        for item in dormant_foreshadows:
            layers["optional"].append(self._item("foreshadow", item, "dormant_ledger"))

        layers["compressed"].append(context_item("story_bible", "story_bible", "Story Bible", "snapshot", snapshot.story_bible))
        for item in snapshot.characters[:12]:
            layers["compressed"].append(self._item("character_state", item, "snapshot"))

        for item in snapshot.chapter_summaries[-3:]:
            layers["recent"].append(self._item("chapter_summary", item, "summary_chain"))
        for item in snapshot.scenes[-5:]:
            layers["recent"].append(self._item("scene", item, "recent_scenes"))

        missing_entities = sorted(set(plan_entities) - set(self._names(matched_entities)))
        missing_locations = sorted(set(plan_locations) - set(self._names(matched_locations)))
        if missing_entities:
            warnings.append("plan_character_missing_from_snapshot")
        if missing_locations:
            warnings.append("plan_location_missing_from_snapshot")

        included_thread_ids = self._ids(active_threads)
        included_foreshadow_ids = self._ids(active_foreshadows)
        coverage = {
            "plan_entities": sorted(plan_entities),
            "matched_entities": sorted(self._names(matched_entities)),
            "missing_entities": missing_entities,
            "plan_locations": sorted(plan_locations),
            "matched_locations": sorted(self._names(matched_locations)),
            "missing_locations": missing_locations,
            "plan_organizations": sorted(plan_organizations),
            "matched_organizations": sorted(self._names(matched_organizations)),
            "missing_organizations": sorted(set(plan_organizations) - set(self._names(matched_organizations))),
            "active_threads_included": included_thread_ids,
            "active_threads_missing": [],
            "foreshadows_included": included_foreshadow_ids,
            "foreshadows_missing": [],
        }

        self._trim_layers(layers)
        audit = build_context_audit(layers, coverage, warnings, self.max_items)
        return ContextPackage(chapter_id=chapter_id, layers=layers, audit=audit)

    def _trim_layers(self, layers: dict[str, list[dict[str, Any]]]) -> None:
        count = 0
        for layer_name in ("mandatory", "compressed", "recent", "optional"):
            kept = []
            for item in layers[layer_name]:
                if count >= self.max_items:
                    break
                kept.append(item)
                count += 1
            layers[layer_name] = kept

    @staticmethod
    def _plan_names(chapter_plan: dict[str, Any], key: str) -> set[str]:
        raw = chapter_plan.get(key)
        if isinstance(raw, list):
            return {str(item).strip() for item in raw if str(item).strip()}
        if isinstance(raw, str) and raw.strip():
            return {item.strip() for item in raw.split(",") if item.strip()}
        return set()

    @staticmethod
    def _match_items(items: list[dict[str, Any]], names: set[str]) -> list[dict[str, Any]]:
        lowered = {name.lower() for name in names}
        matches = []
        for item in items:
            labels = [item.get("name"), item.get("title"), item.get("id")]
            aliases = item.get("aliases") if isinstance(item.get("aliases"), list) else []
            labels.extend(aliases)
            if any(str(label).strip().lower() in lowered for label in labels if label):
                matches.append(item)
        return matches

    @staticmethod
    def _item(kind: str, item: dict[str, Any], source: str) -> dict[str, Any]:
        title = str(item.get("name") or item.get("title") or item.get("id") or kind)
        item_id = str(item.get("id") or title)
        return context_item(kind, item_id, title, source, item)

    @staticmethod
    def _previous_summary(snapshot: NarrativeSnapshot, chapter_id: int) -> dict[str, Any] | None:
        for item in reversed(snapshot.chapter_summaries):
            if item.get("chapter_id") == chapter_id - 1:
                return item
        return None

    @staticmethod
    def _names(items: list[dict[str, Any]]) -> set[str]:
        return {str(item.get("name") or item.get("title") or item.get("id")).strip() for item in items}

    @staticmethod
    def _ids(items: list[dict[str, Any]]) -> list[str]:
        return [str(item.get("id") or item.get("title") or "unknown") for item in items]

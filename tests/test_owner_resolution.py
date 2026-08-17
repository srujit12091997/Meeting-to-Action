"""Owner resolution logic (Days 4-6). Pure logic — runs offline, no API key.

Verifies the core safety behavior: owners are matched against a roster,
and anything we can't confidently match is flagged for human review,
never silently guessed.
"""
from app.graph.nodes import resolve_owners_node
from app.graph.state import PipelineState
from app.schemas.models import ActionItem, MeetingExtraction, OwnerStatus


def _state(items: list[ActionItem], roster: list[str]) -> PipelineState:
    return {
        "extraction": MeetingExtraction(summary="test", action_items=items),
        "known_owners": roster,
    }


def _item(task="do thing", owner=None, status=OwnerStatus.NONE) -> ActionItem:
    return ActionItem(
        task=task, owner=owner, owner_status=status, source_quote="q", confidence=0.9
    )


def test_known_owner_is_resolved_case_insensitively():
    item = _item(owner="raj", status=OwnerStatus.RESOLVED)
    out = resolve_owners_node(_state([item], roster=["Raj", "Priya"]))
    result = out["extraction"].action_items[0]
    assert result.owner == "Raj"  # normalized to roster spelling
    assert result.owner_status == OwnerStatus.RESOLVED
    assert out["needs_review"] is False


def test_unknown_owner_is_flagged_unresolved():
    item = _item(owner="Zoe", status=OwnerStatus.RESOLVED)
    out = resolve_owners_node(_state([item], roster=["Raj", "Priya"]))
    result = out["extraction"].action_items[0]
    assert result.owner_status == OwnerStatus.UNRESOLVED
    assert out["needs_review"] is True


def test_ambiguous_owner_is_never_guessed():
    item = _item(task="update docs", owner=None, status=OwnerStatus.AMBIGUOUS)
    out = resolve_owners_node(_state([item], roster=["Raj", "Priya"]))
    result = out["extraction"].action_items[0]
    assert result.owner is None  # we do NOT fill it in
    assert out["needs_review"] is True


def test_no_owner_mentioned_triggers_review():
    item = _item(owner=None, status=OwnerStatus.NONE)
    out = resolve_owners_node(_state([item], roster=["Raj"]))
    assert out["needs_review"] is True


def test_all_resolved_needs_no_review():
    items = [
        _item(task="a", owner="Raj", status=OwnerStatus.RESOLVED),
        _item(task="b", owner="Priya", status=OwnerStatus.RESOLVED),
    ]
    out = resolve_owners_node(_state(items, roster=["Raj", "Priya"]))
    assert out["needs_review"] is False
    assert all(i.owner_status == OwnerStatus.RESOLVED for i in out["extraction"].action_items)

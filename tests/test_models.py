import json
from hashlib import sha256

from context_integrity.models import (
    AuthorityClass,
    ClassificationConfidence,
    GitFileStatus,
    LifecycleState,
    SourceKind,
    make_source_id,
)


def test_enum_contract():
    enums = [SourceKind, AuthorityClass, LifecycleState, ClassificationConfidence, GitFileStatus]
    for enum in enums:
        for member in enum:
            assert json.loads(json.dumps(member)) == member.value
    assert set(LifecycleState) == {
        "unknown",
        "draft",
        "active",
        "superseded",
        "historical",
        "expired",
        "invalid",
    }
    assert set(ClassificationConfidence) == {"explicit", "strong", "heuristic", "unknown"}


def test_source_id_contract():
    expected = "src_" + sha256(b"repo_one\0docs/Case.md").hexdigest()[:32]
    assert make_source_id("repo_one", "docs/Case.md") == expected
    assert make_source_id("repo_one", "docs/case.md") != expected
    assert make_source_id("repo_two", "docs/Case.md") != expected

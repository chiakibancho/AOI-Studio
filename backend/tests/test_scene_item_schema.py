import pytest
from pydantic import ValidationError

from app.schemas.structure import SceneItem

VALID_SCENE = {
    "number": 1,
    "title": "Opening",
    "duration_sec": 5,
    "description": "desc",
    "shot_type": "B-roll",
    "mood": "calm",
    "notes": "",
}


def test_scene_item_accepts_valid_shape():
    scene = SceneItem.model_validate(VALID_SCENE)
    assert scene.number == 1
    assert scene.duration_sec == 5


def test_scene_item_rejects_missing_required_field():
    broken = dict(VALID_SCENE)
    del broken["duration_sec"]
    with pytest.raises(ValidationError):
        SceneItem.model_validate(broken)


def test_scene_item_rejects_wrong_type():
    broken = dict(VALID_SCENE)
    broken["duration_sec"] = "five"
    with pytest.raises(ValidationError):
        SceneItem.model_validate(broken)

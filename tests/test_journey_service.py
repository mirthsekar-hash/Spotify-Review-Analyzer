"""Journey service unit tests."""

from uuid import uuid4

from src.services.journey_service import (
  JourneyService,
  aggregate_journey_paths,
  build_chain_from_row,
  build_sankey_diagram,
  infer_desired_outcome,
)


def _row(**overrides) -> dict:
  base = {
    "review_id": uuid4(),
    "user_goal": "Discover new artists",
    "listening_behavior": "Uses Discover Weekly",
    "discovery_challenge": "Recommendations feel repetitive",
    "primary_problem": "Uses Instagram Reels for music",
    "sentiment": "negative",
  }
  base.update(overrides)
  return base


def test_build_chain_from_row_builds_five_steps():
  chain = build_chain_from_row(_row())
  assert chain is not None
  assert len(chain) == 5
  assert chain[0] == "Discover new artists"
  assert chain[4] == "Find fresh music"


def test_build_chain_from_row_requires_all_fields():
  assert build_chain_from_row(_row(user_goal="")) is None


def test_infer_desired_outcome_mood_path():
  assert infer_desired_outcome("Relax after work") == "Music that fits the moment"


def test_aggregate_journey_paths_groups_and_sorts():
  rows = [
    _row(),
    _row(),
    _row(
      user_goal="Build workout playlist",
      listening_behavior="Uses Spotify playlists",
      discovery_challenge="Shuffle repeats songs",
      primary_problem="Manually skips tracks",
      sentiment="mixed",
    ),
  ]
  paths = aggregate_journey_paths(rows, limit=5)

  assert len(paths) == 2
  assert paths[0].frequency == 2
  assert paths[0].negative_pct == 100.0
  assert len(paths[0].review_ids) == 2


def test_build_sankey_diagram_produces_links():
  paths = aggregate_journey_paths([_row(), _row()], limit=5)
  diagram = build_sankey_diagram(paths)

  assert diagram.labels
  assert diagram.sources
  assert diagram.targets
  assert diagram.values
  assert sum(diagram.values) > 0


def test_get_journey_paths_disconnected():
  from unittest.mock import patch

  with patch("src.services.journey_service.check_connection", return_value=False):
    data = JourneyService().get_journey_paths()
  assert data.db_connected is False
  assert data.paths == []

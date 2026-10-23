import pytest

from devbrief.core import discovery

pytestmark = pytest.mark.integration


def test_discovery_runs_against_real_machine_state():
    projects = discovery.discover_projects()
    assert isinstance(projects, dict)
    for repo_root, files in projects.items():
        assert repo_root
        assert len(files) > 0

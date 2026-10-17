import pytest


@pytest.fixture(scope="session")
def timeline():
    from crescent_vigil.timeline.store import Timeline
    return Timeline()


@pytest.fixture(scope="session")
def copilot(timeline):
    from crescent_vigil.agent.copilot import Copilot
    return Copilot(timeline=timeline, log=False)

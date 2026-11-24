import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["BAZAAR_SEED"] = "1"

from bazaar.agents import default_roster       # noqa: E402
from bazaar.simulate import run                 # noqa: E402


@pytest.fixture(scope="session")
def roster():
    return default_roster()


@pytest.fixture(scope="session")
def sim():
    return run(n_tasks=240, seed=1)

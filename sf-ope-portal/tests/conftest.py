import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
import pytest
import livedata

@pytest.fixture(autouse=True)
def _offline_by_default(monkeypatch):
    """Tests never hit the network. Live adapters return None (seeded fallback)
    unless a test patches in its own fixtures."""
    monkeypatch.setattr(livedata,'city_record',lambda prop: None)
    monkeypatch.setattr(livedata,'fred_rate',lambda: None)
    monkeypatch.setattr(livedata,'amenities_for',lambda prop: None)
    monkeypatch.setattr(livedata,'str_comps',lambda neighborhood: None)

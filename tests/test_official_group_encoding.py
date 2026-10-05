from pathlib import Path
from app.official_group_earnings import load


def test_group_snapshots_use_utf8_under_ascii_locale(monkeypatch):
    original = Path.read_text

    def ascii_default(path, *args, **kwargs):
        if not args and 'encoding' not in kwargs:
            kwargs['encoding'] = 'ascii'
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', ascii_default)
    pt = load('PT')
    assert len(pt['observations']) == 10
    assert pt['groups']['9'] == 'Trabalhadores não qualificados'
    assert len(load('PK')['observations']) == 120

import pytest

from purchase_pipeline import pipeline


def test_run_notifies_slack_and_reraises_on_failure(monkeypatch):
    notified = []
    monkeypatch.setattr(pipeline, "notify_slack", lambda message: notified.append(message))

    def _boom(config_path, dry_run):
        raise RuntimeError("catalog fetch exploded")

    monkeypatch.setattr(pipeline, "_run", _boom)

    with pytest.raises(RuntimeError, match="catalog fetch exploded"):
        pipeline.run("config.yaml", dry_run=True)

    assert len(notified) == 1
    assert "config.yaml" in notified[0]
    assert "catalog fetch exploded" in notified[0]


def test_run_does_not_notify_on_success(monkeypatch):
    notified = []
    monkeypatch.setattr(pipeline, "notify_slack", lambda message: notified.append(message))
    monkeypatch.setattr(pipeline, "_run", lambda config_path, dry_run: None)

    pipeline.run("config.yaml", dry_run=True)

    assert notified == []

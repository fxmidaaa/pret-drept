from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest

import predict


@pytest.fixture
def cold_bundle(monkeypatch):
    monkeypatch.setattr(predict, "_bundle", None)
    load = Mock(side_effect=lambda _: {"model": object()})
    monkeypatch.setattr(predict.joblib, "load", load)
    return load


def test_concurrent_callers_share_one_complete_bundle(cold_bundle, monkeypatch):
    constructing = Event()
    release = Event()
    second_started = Event()
    explainer = object()

    def build_explainer(model):
        constructing.set()
        assert release.wait(5), "test did not release explainer construction"
        return explainer

    def get_second_bundle():
        second_started.set()
        return predict.get_bundle()

    build = Mock(side_effect=build_explainer)
    monkeypatch.setattr(predict.shap, "TreeExplainer", build)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(predict.get_bundle)
        try:
            assert constructing.wait(5)
            second = pool.submit(get_second_bundle)
            assert second_started.wait(5)
            assert predict._bundle is None
            with pytest.raises(TimeoutError):
                second.result(timeout=0.2)
        finally:
            release.set()

        bundle = first.result(timeout=5)
        assert second.result(timeout=5) is bundle

    assert bundle["explainer"] is explainer
    assert predict.get_bundle() is bundle
    cold_bundle.assert_called_once_with(predict.MODEL_PATH)
    build.assert_called_once_with(bundle["model"])


def test_explainer_failure_leaves_initialization_retryable(cold_bundle, monkeypatch):
    explainer = object()
    build = Mock(side_effect=[RuntimeError("synthetic initialization failure"), explainer])
    monkeypatch.setattr(predict.shap, "TreeExplainer", build)

    with pytest.raises(RuntimeError, match="synthetic initialization failure"):
        predict.get_bundle()

    assert predict._bundle is None
    bundle = predict.get_bundle()
    assert bundle["explainer"] is explainer
    assert predict.get_bundle() is bundle
    assert cold_bundle.call_count == build.call_count == 2

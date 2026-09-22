"""Vérifie que l'évaluation finale nécessite une option explicite."""

from unittest.mock import Mock, call, sentinel

import pytest

import run_pipeline


@pytest.mark.parametrize("evaluate", [False, True])
def test_evaluation_runs_only_when_requested(monkeypatch, evaluate):
    trained_result = (sentinel.model, sentinel.X_test, [0, 1])
    train = Mock(return_value=trained_result)
    evaluation = Mock()
    save = Mock()
    execution = Mock()
    execution.attach_mock(train, "train")
    execution.attach_mock(evaluation, "evaluate")
    execution.attach_mock(save, "save")
    monkeypatch.setattr(run_pipeline, "train_model", train)
    monkeypatch.setattr(run_pipeline, "evaluate_model", evaluation)
    monkeypatch.setattr(run_pipeline, "save_pipeline", save)
    monkeypatch.setattr(run_pipeline, "save_model_metadata", Mock())

    run_pipeline.main(["--evaluate"] if evaluate else [])

    train.assert_called_once_with()
    if evaluate:
        evaluation.assert_called_once_with(*trained_result)
        assert execution.mock_calls == [
            call.train(), call.evaluate(*trained_result), call.save(sentinel.model),
        ]
    else:
        evaluation.assert_not_called()
        save.assert_not_called()


def test_failed_evaluation_does_not_save_pipeline(monkeypatch):
    train = Mock(return_value=(sentinel.model, sentinel.X_test, sentinel.y_test))
    evaluation = Mock(side_effect=ValueError("Évaluation impossible"))
    save = Mock()
    monkeypatch.setattr(run_pipeline, "train_model", train)
    monkeypatch.setattr(run_pipeline, "evaluate_model", evaluation)
    monkeypatch.setattr(run_pipeline, "save_pipeline", save)

    with pytest.raises(ValueError, match="Évaluation impossible"):
        run_pipeline.main(["--evaluate"])

    save.assert_not_called()


def test_tracking_without_final_evaluation(monkeypatch):
    train = Mock(return_value=(sentinel.model, sentinel.X_test, [0, 1]))
    track = Mock(return_value="run-id")
    evaluation = Mock()
    save = Mock()
    monkeypatch.setattr(run_pipeline, "train_model", train)
    monkeypatch.setattr(run_pipeline, "track_experiment", track)
    monkeypatch.setattr(run_pipeline, "evaluate_model", evaluation)
    monkeypatch.setattr(run_pipeline, "save_pipeline", save)

    run_pipeline.main(["--track"])

    track.assert_called_once_with(sentinel.model, None, None)
    evaluation.assert_not_called()
    save.assert_not_called()


@pytest.mark.parametrize("argument, exit_code", [("--help", 0), ("--invalid", 2)])
def test_help_or_invalid_option_does_not_start_training(monkeypatch, argument, exit_code):
    train = Mock()
    evaluation = Mock()
    monkeypatch.setattr(run_pipeline, "train_model", train)
    monkeypatch.setattr(run_pipeline, "evaluate_model", evaluation)

    with pytest.raises(SystemExit) as error:
        run_pipeline.main([argument])

    assert error.value.code == exit_code
    train.assert_not_called()
    evaluation.assert_not_called()

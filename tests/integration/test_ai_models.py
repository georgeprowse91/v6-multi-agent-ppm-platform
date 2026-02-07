from integrations.services.integration.ai_models import AIModelService, ModelStage, ModelTask


def test_ai_model_train_evaluate_deploy_predict():
    service = AIModelService()
    training = service.train_model(ModelTask.SCHEDULE_ESTIMATION, [2.0, 4.0, 6.0])
    model_id = training.record.model_id

    evaluation = service.evaluate_model(model_id, [3.0, 5.0])
    assert evaluation.metrics["samples"] == 2

    deployed = service.deploy_model(model_id)
    assert deployed.stage == ModelStage.DEPLOYED

    prediction = service.predict(model_id, {"weight": 1.1, "complexity": 1.2})
    assert prediction > 0

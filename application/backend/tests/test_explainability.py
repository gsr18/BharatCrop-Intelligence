from fastapi.testclient import TestClient


def test_explainability_models(client: TestClient):
    """Test explainability models endpoint."""
    response = client.get("/api/v1/explainability/models")
    assert response.status_code == 200
    data = response.json()
    assert "analysis_name" in data
    assert "model_name" in data
    assert data["model_name"] == "HistGradientBoostingRegressor"
    assert "notebook_reference" in data


def test_explainability_global(client: TestClient):
    """Test global feature importance endpoint."""
    response = client.get("/api/v1/explainability/global")
    assert response.status_code == 200
    data = response.json()
    assert "method" in data
    assert data["method"] == "permutation_importance"
    assert "importance" in data
    assert len(data["importance"]) == 6
    assert data["importance"][0]["feature"] == "Crop"
    assert data["importance"][0]["importance_mean_mae_increase"] > 0


def test_explainability_evaluation(client: TestClient):
    """Test evaluation metrics endpoint."""
    response = client.get("/api/v1/explainability/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert "evaluation_metrics" in data
    assert "evaluation_period" in data
    assert "highest_mae_groups" in data
    assert data["evaluation_metrics"]["MAE"] > 0
    assert data["evaluation_metrics"]["RMSE"] > 0
    assert 0 < data["evaluation_metrics"]["R2"] < 1


def test_explainability_bias(client: TestClient):
    """Test prediction bias endpoint."""
    response = client.get("/api/v1/explainability/bias")
    assert response.status_code == 200
    data = response.json()
    assert "strongest_overprediction_groups" in data
    assert "strongest_underprediction_groups" in data
    assert len(data["strongest_overprediction_groups"]) > 0
    assert len(data["strongest_underprediction_groups"]) > 0


def test_explainability_uncertainty(client: TestClient):
    """Test uncertainty status endpoint."""
    response = client.get("/api/v1/explainability/uncertainty")
    assert response.status_code == 200
    data = response.json()
    assert "prediction_interval_available" in data
    assert data["prediction_interval_available"] is False
    assert "confidence_calibration_available" in data
    assert data["confidence_calibration_available"] is False
    assert "reason" in data
    assert "limitations" in data


def test_scenarios_yield(client: TestClient):
    """Test year-based yield scenario endpoint."""
    response = client.post(
        "/api/v1/scenarios/yield",
        params={
            "crop": "Rice",
            "season": "Kharif",
            "crop_category": "Individual Crop Candidate",
            "state": "Uttar Pradesh",
            "district": "Meerut",
            "years": [2019, 2020],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "fixed_features" in data
    assert "predictions" in data
    assert len(data["predictions"]) == 2
    assert data["predictions"][0]["year"] == 2019
    assert data["predictions"][1]["year"] == 2020
    assert "training_period" in data
    assert "interpretation" in data
    assert "limitations" in data


def test_scenarios_baseline(client: TestClient):
    """Test baseline scenario endpoint."""
    response = client.get("/api/v1/scenarios/yield/baseline")
    assert response.status_code == 200
    data = response.json()
    assert "baseline_features" in data
    assert "baseline_prediction" in data
    assert "notebook_reference" in data

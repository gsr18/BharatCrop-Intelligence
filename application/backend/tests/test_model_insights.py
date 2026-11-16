from fastapi.testclient import TestClient


def test_model_insights_portfolio(client: TestClient):
    """Test model portfolio endpoint."""
    response = client.get("/api/v1/model-insights/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert "portfolio" in data
    assert "total_components" in data
    assert data["total_components"] == 4
    assert len(data["portfolio"]) == 4
    assert "notebook_reference" in data


def test_model_insights_models(client: TestClient):
    """Test models list endpoint."""
    response = client.get("/api/v1/model-insights/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) == 4
    assert data["models"][0]["registry_id"] == "yield_prediction_individual_crop_hgb"
    assert "notebook_reference" in data


def test_model_insights_yield_model_card(client: TestClient):
    """Test yield model card endpoint."""
    response = client.get("/api/v1/model-insights/models/yield_prediction_individual_crop_hgb")
    assert response.status_code == 200
    data = response.json()
    assert "model_card" in data
    card = data["model_card"]
    assert card["registry_id"] == "yield_prediction_individual_crop_hgb"
    assert card["component_type"] == "trained_model"
    assert card["task"] == "Yield regression"
    assert card["artifact_exists"] is True
    assert card["metadata_exists"] is True
    assert card["artifact_sha256"] is not None
    assert "notebook_reference" in data


def test_model_insights_crop_recommendation_card(client: TestClient):
    """Test crop recommendation model card endpoint."""
    response = client.get("/api/v1/model-insights/models/crop_recommendation")
    assert response.status_code == 200
    data = response.json()
    assert "model_card" in data
    card = data["model_card"]
    assert card["registry_id"] == "crop_recommendation"
    assert card["component_type"] == "derived_ranking_component"
    assert "notebook_reference" in data


def test_model_insights_weather_classifier_card(client: TestClient):
    """Test weather classifier model card endpoint."""
    response = client.get("/api/v1/model-insights/models/weather_low_yield_classifier")
    assert response.status_code == 200
    data = response.json()
    assert "model_card" in data
    card = data["model_card"]
    assert card["registry_id"] == "weather_low_yield_classifier"
    assert card["component_type"] == "experimental_model_evaluation"
    assert card["artifact_exists"] is False
    assert "notebook_reference" in data


def test_model_insights_agricultural_risk_card(client: TestClient):
    """Test agricultural risk model card endpoint."""
    response = client.get("/api/v1/model-insights/models/agricultural_risk_indicators")
    assert response.status_code == 200
    data = response.json()
    assert "model_card" in data
    card = data["model_card"]
    assert card["registry_id"] == "agricultural_risk_indicators"
    assert card["component_type"] == "analytical_output"
    assert "notebook_reference" in data


def test_model_insights_crop_recommendation_evidence(client: TestClient):
    """Test crop recommendation evaluation evidence endpoint."""
    response = client.get("/api/v1/model-insights/models/crop_recommendation/evidence")
    assert response.status_code == 200
    data = response.json()
    assert "evaluation_evidence" in data
    evidence = data["evaluation_evidence"]
    assert evidence["registry_id"] == "crop_recommendation"
    assert evidence["evaluation_period"] == [2023, 2024]
    assert evidence["top1_hit_rate"] > 0
    assert evidence["top3_hit_rate"] > 0
    assert evidence["mean_spearman_correlation"] > 0
    assert "notebook_reference" in data


def test_model_insights_evaluations(client: TestClient):
    """Test evaluations summary endpoint."""
    response = client.get("/api/v1/model-insights/evaluations")
    assert response.status_code == 200
    data = response.json()
    assert "evaluation_summary" in data
    assert len(data["evaluation_summary"]) == 4
    assert "notebook_reference" in data


def test_model_insights_governance(client: TestClient):
    """Test governance status endpoint."""
    response = client.get("/api/v1/model-insights/governance")
    assert response.status_code == 200
    data = response.json()
    assert "policy_rules" in data
    assert "validation_status" in data
    assert "production_approval" in data
    assert data["production_approval"] == "NOT ESTABLISHED"
    assert len(data["policy_rules"]) == 8
    assert "notebook_reference" in data


def test_model_insights_policy_outputs(client: TestClient):
    """Test policy outputs endpoint."""
    response = client.get("/api/v1/model-insights/policy-outputs")
    assert response.status_code == 200
    data = response.json()
    assert "policy_outputs_available" in data
    assert "registry_entry_count" in data
    assert "policy_rule_count" in data
    assert data["registry_entry_count"] == 4
    assert data["policy_rule_count"] == 8
    assert "notebook_reference" in data


def test_model_insights_health(client: TestClient):
    """Test registry health endpoint."""
    response = client.get("/api/v1/model-insights/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "available"
    assert "registry_entries" in data
    assert data["registry_entries"] == 4
    assert "policy_rules" in data
    assert data["policy_rules"] == 8
    assert "notebook_reference" in data


def test_model_insights_not_found(client: TestClient):
    """Test 404 for non-existent model ID."""
    response = client.get("/api/v1/model-insights/models/nonexistent")
    assert response.status_code == 404

import pytest
from fastapi.testclient import TestClient
from app.repos.user_repo import UserRepo
from app.core.security import create_access_token

from sqlmodel import select
from app.models import AssessmentType

def test_create_project_success(client: TestClient, auth_header, session):
    payload = {
        "name": "Year 2025-2026",
        "academic_year_start": 2025,
        "description": "Test project",
        "assessment_types": [
            {"name": "quiz", "weight": 20},
            {"name": "final", "weight": 80}
        ]
    }
    response = client.post("/projects", json=payload, headers=auth_header)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Year 2025-2026"
    assert data["user_id"] == 1

    # Verify assessment types were actually persisted
    stmt = select(AssessmentType).where(AssessmentType.project_id == data["id"])
    ats = session.exec(stmt).all()
    assert len(ats) == 2
    weights_by_name = {at.name: at.weight for at in ats}
    assert weights_by_name == {"quiz": 20, "final": 80}

def test_create_project_weights_must_sum_to_100(client: TestClient, auth_header):
    payload = {
        "name": "Bad Weights",
        "academic_year_start": 2025,
        "assessment_types": [
            {"name": "quiz", "weight": 40},
            {"name": "final", "weight": 50}
        ]
    }
    response = client.post("/projects", json=payload, headers=auth_header)
    assert response.status_code == 400
    assert "weights must sum" in response.json()["detail"].lower()
    
def test_create_project_with_negative_assessment_type_weights(client: TestClient, auth_header):
    payload = {
        "name": "Bad Weights",
        "academic_year_start": 2025,
        "assessment_types": [
            {"name": "quiz", "weight": -1},
            {"name": "final", "weight": 101}
        ]
    }
    response = client.post("/projects", json=payload, headers=auth_header)
    assert response.status_code == 422
    
    

def test_create_project_requires_auth(client: TestClient):
    payload = {"name": "No Auth", "academic_year_start": 2025, "assessment_types": []}
    response = client.post("/projects", json=payload)
    assert response.status_code == 401

def test_get_projects_empty(client: TestClient, auth_header):
    response = client.get("/projects", headers=auth_header)
    assert response.status_code == 200
    assert response.json() == []

def test_get_projects_with_data(client: TestClient, auth_header):
    # Create one project first
    payload = {
        "name": "Proj A",
        "academic_year_start": 2025,
        "assessment_types": [{"name": "final", "weight": 100}]
    }
    client.post("/projects", json=payload, headers=auth_header)

    response = client.get("/projects", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Proj A"

def test_delete_project_success(client: TestClient, auth_header, session):
    # Create a project to delete
    payload = {
        "name": "Delete Me",
        "academic_year_start": 2025,
        "assessment_types": [{"name": "final", "weight": 100}]
    }
    create_resp = client.post("/projects", json=payload, headers=auth_header)
    project_id = create_resp.json()["id"]

    response = client.delete(f"/projects/{project_id}", headers=auth_header)
    assert response.status_code == 204

    # Verify it's gone
    get_resp = client.get("/projects", headers=auth_header)
    assert len(get_resp.json()) == 0

def test_delete_project_not_found(client: TestClient, auth_header):
    response = client.delete("/projects/9999", headers=auth_header)
    assert response.status_code == 404

def test_delete_project_unauthorized(client: TestClient, auth_header, session):
    # Create a second user
    repo = UserRepo()
    user2 = repo.create_user(session, "other@example.com", "hashedpassword")
    session.commit()
    token2 = create_access_token(data={"sub": user2.email})
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Create project as user1
    payload = {
        "name": "Mine",
        "academic_year_start": 2025,
        "assessment_types": [{"name": "final", "weight": 100}]
    }
    create_resp = client.post("/projects", json=payload, headers=auth_header)
    project_id = create_resp.json()["id"]

    # User2 tries to delete it
    response = client.delete(f"/projects/{project_id}", headers=headers2)
    assert response.status_code == 403
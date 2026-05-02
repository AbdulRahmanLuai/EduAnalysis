import pytest
from fastapi.testclient import TestClient
from app.repos.user_repo import UserRepo
from app.core.security import create_access_token
from sqlmodel import select
from app.models import AssessmentType
import io
import pandas as pd

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
    
    

class TestProjectPopulate:

    def create_test_excel(self, data: list[dict]) -> io.BytesIO:
        """Create an in-memory Excel file from a list of dicts."""
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output
    
    def test_populate_success(self, client, auth_header, session):
        # 1. Create a project with assessment types
        payload = {
            "name": "Test Populate",
            "academic_year_start": 2025,
            "assessment_types": [
                {"name": "quiz", "weight": 20},
                {"name": "final", "weight": 80}
            ]
        }
        resp = client.post("/projects", json=payload, headers=auth_header)
        assert resp.status_code == 201
        project_id = resp.json()["id"]

        # 2. Build a valid Excel file
        excel_data = [
            {"term": 1, "grade": 10, "section": "A", "student_id": 1001, "student_name": "Alice", "course_code": "MATH101", "quiz": 15, "final": 70},
            {"term": 1, "grade": 10, "section": "A", "student_id": 1002, "student_name": "Bob",   "course_code": "MATH101", "quiz": 12, "final": 55},
            {"term": 2, "grade": 10, "section": "A", "student_id": 1001, "student_name": "Alice", "course_code": "MATH101", "quiz": 18, "final": 82},
        ]
        test_file = self.create_test_excel(excel_data)

        # 3. Upload
        resp = client.post(
            f"/projects/{project_id}/populate",
            files={"file": ("test.xlsx", test_file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_header
        )
        assert resp.status_code == 200
        assert resp.json() == {"message": "Project populated successfully"}

        # 4. Verify project is now populated
        proj_resp = client.get(f"/projects", headers=auth_header)
        projects = proj_resp.json()
        assert any(p["id"] == project_id for p in projects)  # should still appear

        # 5. Verify database contents (optional deep check)
        from sqlmodel import select
        from app.models import Semester, Section, Course, Student, CourseOffering, Mark
        semesters = session.exec(select(Semester).where(Semester.project_id == project_id)).all()
        sections = session.exec(select(Section).where(Section.project_id == project_id)).all()
        courses = session.exec(select(Course).where(Course.project_id == project_id)).all()
        students = session.exec(select(Student).where(Student.project_id == project_id)).all()
        marks = session.exec(select(Mark).where(Mark.student.has(project_id=project_id))).all()
        assert len(semesters) == 2
        assert len(sections) == 1
        assert len(courses) == 1
        assert len(students) == 2
        assert len(marks) == 6  # 3 rows × 2 assessment types

    def test_populate_already_populated(self, client, auth_header):
        # Create and populate project once
        payload = {
            "name": "Already Populated",
            "academic_year_start": 2025,
            "assessment_types": [{"name": "quiz", "weight": 100}]
        }
        resp = client.post("/projects", json=payload, headers=auth_header)
        project_id = resp.json()["id"]

        excel_data = [{"term": 1, "grade": 10, "section": "A", "student_id": 1, "student_name": "X", "course_code": "C1", "quiz": 50}]
        test_file = self.create_test_excel(excel_data)
        client.post(f"/projects/{project_id}/populate", files={"file": ("t.xlsx", test_file)}, headers=auth_header)

        # Try again
        test_file2 = self.create_test_excel(excel_data)  # new BytesIO
        resp = client.post(f"/projects/{project_id}/populate", files={"file": ("t.xlsx", test_file2)}, headers=auth_header)
        assert resp.status_code == 400
        assert "already populated" in resp.json()["detail"].lower()

    def test_populate_invalid_file_extension(self, client, auth_header):
        payload = {
            "name": "Bad File",
            "academic_year_start": 2025,
            "assessment_types": [{"name": "quiz", "weight": 100}]
        }
        resp = client.post("/projects", json=payload, headers=auth_header)
        project_id = resp.json()["id"]

        pdf_file = io.BytesIO(b"%PDF-1.4 fake pdf")
        resp = client.post(
            f"/projects/{project_id}/populate",
            files={"file": ("fake.pdf", pdf_file, "application/pdf")},
            headers=auth_header
        )
        assert resp.status_code == 400
        assert "Only" in resp.json()["detail"]

    def test_populate_missing_columns(self, client, auth_header):
        payload = {
            "name": "Missing Cols",
            "academic_year_start": 2025,
            "assessment_types": [{"name": "quiz", "weight": 100}]
        }
        resp = client.post("/projects", json=payload, headers=auth_header)
        project_id = resp.json()["id"]

        # Missing 'section' and 'student_name'
        excel_data = [{"term": 1, "grade": 10, "student_id": 1, "course_code": "C1", "quiz": 50}]
        test_file = self.create_test_excel(excel_data)
        resp = client.post(
            f"/projects/{project_id}/populate",
            files={"file": ("test.xlsx", test_file)},
            headers=auth_header
        )
        assert resp.status_code == 400
        assert "missing columns" in resp.json()["detail"].lower()

    def test_populate_unauthorized(self, client, auth_header, session):
        # Create project as test user
        payload = {
            "name": "Unauth Pop",
            "academic_year_start": 2025,
            "assessment_types": [{"name": "quiz", "weight": 100}]
        }
        resp = client.post("/projects", json=payload, headers=auth_header)
        project_id = resp.json()["id"]

        # Create second user and token
        from app.repos.user_repo import UserRepo
        from app.core.security import create_access_token, hash_password
        repo = UserRepo()
        user2 = repo.create_user(session, "other@example.com", hash_password("pass"))
        session.commit()
        token2 = create_access_token(data={"sub": user2.email})
        headers2 = {"Authorization": f"Bearer {token2}"}

        excel_data = [{"term": 1, "grade": 10, "section": "A", "student_id": 1, "student_name": "X", "course_code": "C1", "quiz": 50}]
        test_file = self.create_test_excel(excel_data)
        resp = client.post(
            f"/projects/{project_id}/populate",
            files={"file": ("test.xlsx", test_file)},
            headers=headers2
        )
        assert resp.status_code == 403

    def test_populate_project_not_found(self, client, auth_header):
        excel_data = [{"term": 1, "grade": 10, "section": "A", "student_id": 1, "student_name": "X", "course_code": "C1", "quiz": 50}]
        test_file = self.create_test_excel(excel_data)
        resp = client.post(
            "/projects/9999/populate",
            files={"file": ("test.xlsx", test_file)},
            headers=auth_header
        )
        assert resp.status_code == 404
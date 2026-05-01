from fastapi.testclient import TestClient


class TestSignup:
    def test_signup_success(self, client: TestClient):
        payload = {"email": "newuser@example.com", "password": "securepass123"}
        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_signup_duplicate_email(self, client: TestClient, test_user):
        payload = {
            "email": test_user["user"].email,
            "password": "anotherpass"
        }
        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_signup_invalid_email(self, client: TestClient):
        payload = {"email": "not-an-email", "password": "pass"}
        response = client.post("/auth/signup", json=payload)
        assert response.status_code == 422  # Pydantic validation error


class TestLogin:
    def test_login_success(self, client: TestClient, test_user):
        payload = {
            "email": test_user["user"].email,
            "password": test_user["password"]   # raw password from fixture
        }
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient, test_user):
        payload = {
            "email": test_user["user"].email,
            "password": "wrongpass"
        }
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        payload = {"email": "ghost@example.com", "password": "nopass"}
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["detail"].lower()
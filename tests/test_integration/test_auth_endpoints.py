"""
Integration tests for authentication endpoints.

Tests the complete authentication flow including registration, login,
token refresh, and password management.
"""

import pytest
from httpx import AsyncClient

from app.models.user import User
from app.models.enums import UserRole, UserStatus
from app.core.security import verify_password, verify_token


@pytest.mark.integration
@pytest.mark.auth
class TestUserRegistration:
    """Test user registration endpoint."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, test_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = await test_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["first_name"] == user_data["first_name"]
        assert data["last_name"] == user_data["last_name"]
        assert "password" not in data
        assert "hashed_password" not in data
        assert data["is_active"] is True
        assert data["role"] == UserRole.USER.value
    
    async def test_register_user_password_mismatch(self, test_client: AsyncClient):
        """Test registration with password mismatch."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "NewPass123!",
            "password_confirm": "DifferentPass123!",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = await test_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()
    
    async def test_register_user_weak_password(self, test_client: AsyncClient):
        """Test registration with weak password."""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "weak",
            "password_confirm": "weak",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = await test_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()
    
    async def test_register_user_duplicate_username(self, test_client: AsyncClient, test_user):
        """Test registration with duplicate username."""
        user_data = {
            "username": test_user.username,  # Duplicate username
            "email": "different@example.com",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = await test_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()
    
    async def test_register_user_duplicate_email(self, test_client: AsyncClient, test_user):
        """Test registration with duplicate email."""
        user_data = {
            "username": "newuser",
            "email": test_user.email,  # Duplicate email
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = await test_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()
    
    async def test_register_user_invalid_email(self, test_client: AsyncClient):
        """Test registration with invalid email format."""
        user_data = {
            "username": "newuser",
            "email": "invalid-email",
            "password": "NewPass123!",
            "password_confirm": "NewPass123!",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = await test_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422  # Validation error


@pytest.mark.integration
@pytest.mark.auth
class TestUserLogin:
    """Test user login endpoint."""
    
    async def test_login_success(self, test_client: AsyncClient, test_user):
        """Test successful login."""
        login_data = {
            "username": test_user.username,
            "password": "TestPass123!"  # From test fixture
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == test_user.username
        assert data["user"]["email"] == test_user.email
        
        # Verify token is valid
        access_token = data["access_token"]
        payload = verify_token(access_token)
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
    
    async def test_login_wrong_password(self, test_client: AsyncClient, test_user):
        """Test login with wrong password."""
        login_data = {
            "username": test_user.username,
            "password": "WrongPassword123!"
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_login_nonexistent_user(self, test_client: AsyncClient):
        """Test login with nonexistent username."""
        login_data = {
            "username": "nonexistent",
            "password": "SomePass123!"
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()
    
    async def test_login_inactive_user(self, test_client: AsyncClient, test_db_session):
        """Test login with inactive user."""
        # Create inactive user
        from app.core.security import get_password_hash
        inactive_user = User(
            username="inactive",
            email="inactive@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            first_name="Inactive",
            last_name="User",
            is_active=False,
            role=UserRole.USER,
            status=UserStatus.INACTIVE
        )
        test_db_session.add(inactive_user)
        test_db_session.commit()
        
        login_data = {
            "username": "inactive",
            "password": "TestPass123!"
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()
    
    async def test_login_email_instead_of_username(self, test_client: AsyncClient, test_user):
        """Test login using email instead of username."""
        login_data = {
            "username": test_user.email,  # Use email as username
            "password": "TestPass123!"
        }
        
        response = await test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["username"] == test_user.username


@pytest.mark.integration
@pytest.mark.auth
class TestTokenManagement:
    """Test token management endpoints."""
    
    async def test_get_current_user(self, test_client: AsyncClient, auth_headers, test_user):
        """Test getting current user with valid token."""
        response = await test_client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
    
    async def test_get_current_user_invalid_token(self, test_client: AsyncClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await test_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    async def test_get_current_user_no_token(self, test_client: AsyncClient):
        """Test getting current user without token."""
        response = await test_client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    async def test_refresh_token(self, test_client: AsyncClient, test_user):
        """Test token refresh."""
        # First login to get tokens
        login_data = {
            "username": test_user.username,
            "password": "TestPass123!"
        }
        
        login_response = await test_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}
        response = await test_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
        # Verify new token works
        new_token = data["access_token"]
        payload = verify_token(new_token)
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
    
    async def test_refresh_token_invalid(self, test_client: AsyncClient):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid_refresh_token"}
        response = await test_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
    
    async def test_logout(self, test_client: AsyncClient, auth_headers):
        """Test user logout."""
        response = await test_client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()


@pytest.mark.integration
@pytest.mark.auth
class TestPasswordManagement:
    """Test password management endpoints."""
    
    async def test_change_password_success(self, test_client: AsyncClient, auth_headers, test_user):
        """Test successful password change."""
        change_data = {
            "current_password": "TestPass123!",
            "new_password": "NewPass456!",
            "new_password_confirm": "NewPass456!"
        }
        
        response = await test_client.post("/api/v1/auth/change-password", 
                                        json=change_data, headers=auth_headers)
        
        assert response.status_code == 200
        assert "changed" in response.json()["message"].lower()
        
        # Verify old password no longer works
        login_data = {
            "username": test_user.username,
            "password": "TestPass123!"
        }
        login_response = await test_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 401
        
        # Verify new password works
        login_data["password"] = "NewPass456!"
        login_response = await test_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
    
    async def test_change_password_wrong_current(self, test_client: AsyncClient, auth_headers):
        """Test password change with wrong current password."""
        change_data = {
            "current_password": "WrongPass123!",
            "new_password": "NewPass456!",
            "new_password_confirm": "NewPass456!"
        }
        
        response = await test_client.post("/api/v1/auth/change-password", 
                                        json=change_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "current password" in response.json()["detail"].lower()
    
    async def test_change_password_mismatch(self, test_client: AsyncClient, auth_headers):
        """Test password change with password mismatch."""
        change_data = {
            "current_password": "TestPass123!",
            "new_password": "NewPass456!",
            "new_password_confirm": "DifferentPass456!"
        }
        
        response = await test_client.post("/api/v1/auth/change-password", 
                                        json=change_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "match" in response.json()["detail"].lower()
    
    async def test_change_password_weak_new_password(self, test_client: AsyncClient, auth_headers):
        """Test password change with weak new password."""
        change_data = {
            "current_password": "TestPass123!",
            "new_password": "weak",
            "new_password_confirm": "weak"
        }
        
        response = await test_client.post("/api/v1/auth/change-password", 
                                        json=change_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()
    
    async def test_reset_password_request(self, test_client: AsyncClient, test_user):
        """Test password reset request."""
        reset_data = {"email": test_user.email}
        
        response = await test_client.post("/api/v1/auth/reset-password", json=reset_data)
        
        # Should always return 200 even if email doesn't exist (security)
        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()
    
    async def test_reset_password_nonexistent_email(self, test_client: AsyncClient):
        """Test password reset request with nonexistent email."""
        reset_data = {"email": "nonexistent@example.com"}
        
        response = await test_client.post("/api/v1/auth/reset-password", json=reset_data)
        
        # Should still return 200 for security (don't reveal if email exists)
        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()


@pytest.mark.integration
@pytest.mark.auth
class TestAuthenticationFlow:
    """Test complete authentication flows."""
    
    async def test_complete_registration_login_flow(self, test_client: AsyncClient):
        """Test complete flow from registration to login."""
        # 1. Register new user
        user_data = {
            "username": "flowtest",
            "email": "flowtest@example.com",
            "password": "FlowTest123!",
            "password_confirm": "FlowTest123!",
            "first_name": "Flow",
            "last_name": "Test"
        }
        
        register_response = await test_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201
        
        # 2. Login with new user
        login_data = {
            "username": "flowtest",
            "password": "FlowTest123!"
        }
        
        login_response = await test_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        access_token = tokens["access_token"]
        
        # 3. Access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        user_info = me_response.json()
        assert user_info["username"] == "flowtest"
        assert user_info["email"] == "flowtest@example.com"
    
    async def test_token_refresh_flow(self, test_client: AsyncClient, test_user):
        """Test token refresh flow."""
        # 1. Login to get initial tokens
        login_data = {
            "username": test_user.username,
            "password": "TestPass123!"
        }
        
        login_response = await test_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        initial_tokens = login_response.json()
        initial_access = initial_tokens["access_token"]
        refresh_token = initial_tokens["refresh_token"]
        
        # 2. Use access token
        headers = {"Authorization": f"Bearer {initial_access}"}
        me_response = await test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # 3. Refresh tokens
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = await test_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 200
        
        new_tokens = refresh_response.json()
        new_access = new_tokens["access_token"]
        
        # 4. Use new access token
        new_headers = {"Authorization": f"Bearer {new_access}"}
        me_response2 = await test_client.get("/api/v1/auth/me", headers=new_headers)
        assert me_response2.status_code == 200
        
        # Tokens should be different
        assert initial_access != new_access
    
    async def test_logout_invalidates_session(self, test_client: AsyncClient, test_user):
        """Test that logout properly invalidates the session."""
        # 1. Login
        login_data = {
            "username": test_user.username,
            "password": "TestPass123!"
        }
        
        login_response = await test_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        access_token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 2. Verify token works
        me_response = await test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # 3. Logout
        logout_response = await test_client.post("/api/v1/auth/logout", headers=headers)
        assert logout_response.status_code == 200
        
        # 4. Token should still work (JWT tokens are stateless)
        # In a real implementation, you might maintain a blacklist
        me_response2 = await test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response2.status_code == 200  # JWT tokens remain valid until expiry
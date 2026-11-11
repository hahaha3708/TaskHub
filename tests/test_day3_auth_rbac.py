from collections.abc import AsyncIterator

import jwt
import pytest
import pytest_asyncio
from app.core.config import settings
from app.core.constants import JWT_ALGORITHM
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models import User, UserRole
from app.schemas.auth import LoginRequest
from app.schemas.user import ChangePasswordRequest, UserCreate
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


async def register(
    client: AsyncClient, email: str, password: str = "pass12345"
) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test User", "password": password},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def login(client: AsyncClient, email: str, password: str = "pass12345") -> dict:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_refresh_token_cannot_authenticate_access_endpoint(
    client: AsyncClient,
) -> None:
    await register(client, "refresh-type@example.com")
    tokens = await login(client, "refresh-type@example.com")

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_signed_token_with_invalid_subject_returns_401(
    client: AsyncClient,
) -> None:
    token = jwt.encode(
        {"sub": "not-an-id", "type": "access", "jti": "test-jti"},
        settings.secret_key,
        algorithm=JWT_ALGORITHM,
    )
    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_reusing_refresh_token_revokes_rotated_session(
    client: AsyncClient,
) -> None:
    await register(client, "rotation@example.com")
    original = await login(client, "rotation@example.com")
    rotated = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original["refresh_token"]}
    )
    assert rotated.status_code == 200

    reuse = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original["refresh_token"]}
    )
    assert reuse.status_code == 401
    assert reuse.headers["www-authenticate"] == "Bearer"
    revoked_rotated = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
    )
    assert revoked_rotated.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_registration_returns_conflict(client: AsyncClient) -> None:
    await register(client, "duplicate@example.com")

    duplicate = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "duplicate@example.com",
            "full_name": "Other",
            "password": "pass12345",
        },
    )

    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_member_cannot_edit_or_delete_another_user(client: AsyncClient) -> None:
    await register(client, "member-a@example.com")
    target = await register(client, "member-b@example.com")
    tokens = await login(client, "member-a@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    update = await client.patch(
        f"/api/v1/users/{target['id']}",
        headers=headers,
        json={"full_name": "Taken over"},
    )
    delete = await client.delete(f"/api/v1/users/{target['id']}", headers=headers)

    assert update.status_code == 403
    assert delete.status_code == 403


@pytest.mark.asyncio
async def test_member_cannot_change_or_delete_another_users_workspace(
    client: AsyncClient,
) -> None:
    await register(client, "workspace-a@example.com")
    await register(client, "workspace-b@example.com")
    a_tokens = await login(client, "workspace-a@example.com")
    b_tokens = await login(client, "workspace-b@example.com")
    b_headers = {"Authorization": f"Bearer {b_tokens['access_token']}"}
    a_headers = {"Authorization": f"Bearer {a_tokens['access_token']}"}
    created = await client.post(
        "/api/v1/workspaces/", headers=b_headers, json={"name": "B private"}
    )
    workspace_id = created.json()["id"]

    update = await client.patch(
        f"/api/v1/workspaces/{workspace_id}", headers=a_headers, json={"name": "stolen"}
    )
    delete = await client.delete(
        f"/api/v1/workspaces/{workspace_id}", headers=a_headers
    )

    assert update.status_code == 403
    assert delete.status_code == 403


@pytest.mark.asyncio
async def test_workspace_listing_membership_and_role_management(
    client: AsyncClient,
) -> None:
    owner = await register(client, "workspace-owner@example.com")
    member = await register(client, "workspace-member@example.com")
    owner_tokens = await login(client, "workspace-owner@example.com")
    member_tokens = await login(client, "workspace-member@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}
    member_headers = {"Authorization": f"Bearer {member_tokens['access_token']}"}

    created = await client.post(
        "/api/v1/workspaces/", headers=owner_headers, json={"name": "Planning"}
    )
    workspace_id = created.json()["id"]
    owner_workspaces = await client.get("/api/v1/workspaces/", headers=owner_headers)
    member_workspaces = await client.get("/api/v1/workspaces/", headers=member_headers)
    assert len(owner_workspaces.json()) == 1
    assert member_workspaces.json() == []

    invited = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={"user_id": member["id"], "role": "VIEWER"},
    )
    assert invited.status_code == 201
    assert invited.json()["role"] == "VIEWER"
    member_workspaces = await client.get("/api/v1/workspaces/", headers=member_headers)
    assert len(member_workspaces.json()) == 1

    members = await client.get(
        f"/api/v1/workspaces/{workspace_id}/members", headers=member_headers
    )
    assert members.status_code == 200
    assert {item["user_id"] for item in members.json()} == {owner["id"], member["id"]}

    member_workspace_update = await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        headers=member_headers,
        json={"name": "Not allowed"},
    )
    member_role_update = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{member['id']}",
        headers=member_headers,
        json={"role": "EDITOR"},
    )
    member_removal = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{member['id']}",
        headers=member_headers,
    )
    assert member_workspace_update.status_code == 403
    assert member_role_update.status_code == 403
    assert member_removal.status_code == 403

    changed = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{member['id']}",
        headers=owner_headers,
        json={"role": "EDITOR"},
    )
    assert changed.status_code == 200
    assert changed.json()["role"] == "EDITOR"

    attempted_owner = await client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{member['id']}",
        headers=owner_headers,
        json={"role": "OWNER"},
    )
    assert attempted_owner.status_code == 422

    removed = await client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{member['id']}",
        headers=owner_headers,
    )
    assert removed.status_code == 204
    member_workspaces = await client.get("/api/v1/workspaces/", headers=member_headers)
    assert member_workspaces.json() == []


@pytest.mark.asyncio
async def test_workspace_invitation_rejects_missing_and_duplicate_users(
    client: AsyncClient,
) -> None:
    await register(client, "invite-owner@example.com")
    member = await register(client, "invite-member@example.com")
    owner_tokens = await login(client, "invite-owner@example.com")
    headers = {"Authorization": f"Bearer {owner_tokens['access_token']}"}
    created = await client.post(
        "/api/v1/workspaces/", headers=headers, json={"name": "Invites"}
    )
    workspace_id = created.json()["id"]

    first = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=headers,
        json={"user_id": member["id"]},
    )
    duplicate = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=headers,
        json={"user_id": member["id"]},
    )
    missing = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=headers,
        json={"user_id": 99999},
    )
    owner_role = await client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=headers,
        json={"user_id": member["id"], "role": "OWNER"},
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert missing.status_code == 404
    assert owner_role.status_code == 422


@pytest.mark.asyncio
async def test_workspace_owner_can_update_and_delete_workspace(
    client: AsyncClient,
) -> None:
    await register(client, "workspace-crud@example.com")
    tokens = await login(client, "workspace-crud@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    created = await client.post(
        "/api/v1/workspaces/", headers=headers, json={"name": "Before"}
    )
    workspace_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        headers=headers,
        json={"name": "After"},
    )
    deleted = await client.delete(f"/api/v1/workspaces/{workspace_id}", headers=headers)

    assert updated.status_code == 200
    assert updated.json()["name"] == "After"
    assert deleted.status_code == 204
    assert (
        await client.get(f"/api/v1/workspaces/{workspace_id}", headers=headers)
    ).status_code == 404


@pytest.mark.asyncio
async def test_password_change_rejects_old_password(client: AsyncClient) -> None:
    await register(client, "password-change@example.com")
    tokens = await login(client, "password-change@example.com")
    changed = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"old_password": "pass12345", "new_password": "newpass123"},
    )
    assert changed.status_code == 204

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "password-change@example.com", "password": "pass12345"},
    )
    assert old_login.status_code == 401


@pytest.mark.asyncio
async def test_registration_ignores_client_role(client: AsyncClient) -> None:
    user = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "no-role-escalation@example.com",
            "full_name": "Member",
            "password": "pass12345",
            "role": "ADMIN",
        },
    )
    assert user.status_code == 201
    assert user.json()["role"] == UserRole.MEMBER.value


@pytest.mark.asyncio
async def test_last_admin_cannot_demote_or_delete_self(client: AsyncClient) -> None:
    admin = await register(client, "admin@example.com")
    session_generator = app.dependency_overrides[get_session]()
    session = await anext(session_generator)
    user = await session.get(User, admin["id"])
    user.role = UserRole.ADMIN
    await session.commit()
    await session_generator.aclose()
    tokens = await login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    demote = await client.patch(
        f"/api/v1/users/{admin['id']}", headers=headers, json={"role": "MEMBER"}
    )
    delete = await client.delete(f"/api/v1/users/{admin['id']}", headers=headers)

    assert demote.status_code == 403
    assert delete.status_code == 403


def test_password_schemas_enforce_bcrypt_byte_limit() -> None:
    password_72_bytes = "é" * 36
    password_74_bytes = "é" * 37

    UserCreate.model_validate(
        {
            "email": "limit@example.com",
            "full_name": "Limit",
            "password": password_72_bytes,
        }
    )
    LoginRequest(email="limit@example.com", password=password_72_bytes)
    ChangePasswordRequest(
        old_password=password_72_bytes,
        new_password=password_72_bytes,
    )

    with pytest.raises(ValidationError):
        UserCreate.model_validate(
            {
                "email": "limit@example.com",
                "full_name": "Limit",
                "password": password_74_bytes,
            }
        )
    with pytest.raises(ValidationError):
        LoginRequest(email="limit@example.com", password=password_74_bytes)
    with pytest.raises(ValidationError):
        ChangePasswordRequest(
            old_password="pass12345",
            new_password=password_74_bytes,
        )

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.enums import TaskPriority, TaskStatus, UserRole, WorkspaceRole
from app.models.user import User
from httpx import ASGITransport, AsyncClient
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


async def register_user(
    client: AsyncClient, email: str, name: str = "Test User"
) -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": name, "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def login_user(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest_asyncio.fixture
async def setup_env(client: AsyncClient) -> dict:
    owner = await register_user(client, "owner@example.com", "Workspace Owner")
    editor = await register_user(client, "editor@example.com", "Workspace Editor")
    viewer = await register_user(client, "viewer@example.com", "Workspace Viewer")
    outsider = await register_user(client, "outsider@example.com", "Outsider")
    admin = await register_user(client, "admin@example.com", "System Admin")

    # Set admin role in DB
    session_generator = app.dependency_overrides[get_session]()
    session = await anext(session_generator)
    db_admin = await session.get(User, admin["id"])
    assert db_admin is not None
    db_admin.role = UserRole.ADMIN
    await session.commit()
    await session_generator.aclose()

    owner_hdr = await login_user(client, "owner@example.com")
    editor_hdr = await login_user(client, "editor@example.com")
    viewer_hdr = await login_user(client, "viewer@example.com")
    outsider_hdr = await login_user(client, "outsider@example.com")
    admin_hdr = await login_user(client, "admin@example.com")

    # Create workspace
    ws_resp = await client.post(
        "/api/v1/workspaces/",
        headers=owner_hdr,
        json={"name": "Engineering Workspace"},
    )
    assert ws_resp.status_code == 201, ws_resp.text
    workspace = ws_resp.json()

    # Add editor and viewer
    add_ed = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        headers=owner_hdr,
        json={"user_id": editor["id"], "role": WorkspaceRole.EDITOR.value},
    )
    assert add_ed.status_code == 201, add_ed.text

    add_vi = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/members",
        headers=owner_hdr,
        json={"user_id": viewer["id"], "role": WorkspaceRole.VIEWER.value},
    )
    assert add_vi.status_code == 201, add_vi.text

    # Create project
    proj_resp = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/projects",
        headers=owner_hdr,
        json={"name": "Backend API", "description": "Core services"},
    )
    assert proj_resp.status_code == 201, proj_resp.text
    project = proj_resp.json()

    return {
        "workspace": workspace,
        "project": project,
        "owner": owner,
        "editor": editor,
        "viewer": viewer,
        "outsider": outsider,
        "admin": admin,
        "owner_hdr": owner_hdr,
        "editor_hdr": editor_hdr,
        "viewer_hdr": viewer_hdr,
        "outsider_hdr": outsider_hdr,
        "admin_hdr": admin_hdr,
    }


# ============================================================================
# 1. PERMISSIONS & RBAC TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_viewer_write_forbidden(client: AsyncClient, setup_env: dict) -> None:
    project_id = setup_env["project"]["id"]
    viewer_hdr = setup_env["viewer_hdr"]

    # VIEWER cannot create task -> 403
    create_task = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=viewer_hdr,
        json={"title": "Unauthorized task"},
    )
    assert create_task.status_code == 403

    # VIEWER cannot create label -> 403
    create_label = await client.post(
        f"/api/v1/projects/{project_id}/labels",
        headers=viewer_hdr,
        json={"name": "Bug", "color": "#ff0000"},
    )
    assert create_label.status_code == 403

    # Create a task by owner
    task_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=setup_env["owner_hdr"],
        json={"title": "Owner task"},
    )
    task_id = task_resp.json()["id"]

    # VIEWER cannot update or delete task -> 403
    update_task = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=viewer_hdr,
        json={"title": "Viewer hacked"},
    )
    assert update_task.status_code == 403

    delete_task = await client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=viewer_hdr,
    )
    assert delete_task.status_code == 403

    # VIEWER cannot add comment -> 403
    add_comment = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=viewer_hdr,
        json={"content": "Viewer comment"},
    )
    assert add_comment.status_code == 403


@pytest.mark.asyncio
async def test_outsider_access_returns_forbidden(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    outsider_hdr = setup_env["outsider_hdr"]

    # Outsider cannot read or write tasks in project -> 403
    list_tasks = await client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=outsider_hdr,
    )
    assert list_tasks.status_code == 403

    create_task = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=outsider_hdr,
        json={"title": "Outsider task"},
    )
    assert create_task.status_code == 403

    # Create task by owner
    task_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=setup_env["owner_hdr"],
        json={"title": "Owner task"},
    )
    task_id = task_resp.json()["id"]

    # Outsider cannot get, update, or delete task -> 403
    get_task = await client.get(f"/api/v1/tasks/{task_id}", headers=outsider_hdr)
    assert get_task.status_code == 403

    patch_task = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=outsider_hdr,
        json={"title": "Outsider edit"},
    )
    assert patch_task.status_code == 403

    delete_task = await client.delete(f"/api/v1/tasks/{task_id}", headers=outsider_hdr)
    assert delete_task.status_code == 403


@pytest.mark.asyncio
async def test_admin_bypasses_workspace_rbac(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    admin_hdr = setup_env["admin_hdr"]

    # Admin is not explicitly added to workspace_members, but has full access
    create_task = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=admin_hdr,
        json={"title": "Admin task"},
    )
    assert create_task.status_code == 201
    task = create_task.json()

    # Admin can update task
    update_task = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        headers=admin_hdr,
        json={"title": "Admin task updated"},
    )
    assert update_task.status_code == 200
    assert update_task.json()["title"] == "Admin task updated"

    # Admin can delete task
    delete_task = await client.delete(
        f"/api/v1/tasks/{task['id']}",
        headers=admin_hdr,
    )
    assert delete_task.status_code == 204


# ============================================================================
# 2. DATA VALIDATION & CONSTRAINTS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_assignee_must_be_workspace_member(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    owner_hdr = setup_env["owner_hdr"]
    outsider_id = setup_env["outsider"]["id"]
    editor_id = setup_env["editor"]["id"]

    # Assigning to outsider -> 422
    invalid_create = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Invalid assignee", "assignee_id": outsider_id},
    )
    assert invalid_create.status_code == 422

    # Assigning to member -> 201
    valid_create = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Valid assignee", "assignee_id": editor_id},
    )
    assert valid_create.status_code == 201
    task = valid_create.json()
    assert task["assignee_id"] == editor_id

    # Updating assignee to outsider -> 422
    invalid_update = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        headers=owner_hdr,
        json={"assignee_id": outsider_id},
    )
    assert invalid_update.status_code == 422


@pytest.mark.asyncio
async def test_due_date_cannot_be_in_past(client: AsyncClient, setup_env: dict) -> None:
    project_id = setup_env["project"]["id"]
    owner_hdr = setup_env["owner_hdr"]

    past_date = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    future_date = (datetime.now(UTC) + timedelta(days=2)).isoformat()

    # Past due_date -> 422
    past_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Past task", "due_date": past_date},
    )
    assert past_resp.status_code == 422

    # Future due_date -> 201
    future_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Future task", "due_date": future_date},
    )
    assert future_resp.status_code == 201


@pytest.mark.asyncio
async def test_task_creation_default_status_is_todo(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    owner_hdr = setup_env["owner_hdr"]

    # Even if client tries to send status="DONE", status defaults to TODO
    resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Default status task", "status": "DONE"},
    )
    assert resp.status_code == 201
    task = resp.json()
    assert task["status"] == TaskStatus.TODO.value
    assert task["created_by"] == setup_env["owner"]["id"]


# ============================================================================
# 3. PROJECT ARCHIVE & UNARCHIVE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_archived_project_blocks_writes(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    owner_hdr = setup_env["owner_hdr"]
    viewer_hdr = setup_env["viewer_hdr"]

    # Create task before archiving
    task_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Pre-archive task"},
    )
    task_id = task_resp.json()["id"]

    # Archive project
    archive_resp = await client.post(
        f"/api/v1/projects/{project_id}/archive",
        headers=owner_hdr,
    )
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "ARCHIVED"

    # Permission check happens before archive check:
    # VIEWER write attempt gets 403, NOT 409!
    viewer_create = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=viewer_hdr,
        json={"title": "Viewer task"},
    )
    assert viewer_create.status_code == 403

    # Authorized writer (OWNER/EDITOR) gets 409 Conflict when
    # writing to archived project!
    create_task = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Cannot write to archived"},
    )
    assert create_task.status_code == 409

    update_task = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=owner_hdr,
        json={"title": "Cannot edit archived"},
    )
    assert update_task.status_code == 409

    delete_task = await client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=owner_hdr,
    )
    assert delete_task.status_code == 409

    # Unarchive project
    unarchive_resp = await client.post(
        f"/api/v1/projects/{project_id}/unarchive",
        headers=owner_hdr,
    )
    assert unarchive_resp.status_code == 200
    assert unarchive_resp.json()["status"] == "ACTIVE"

    # Writes succeed after unarchive
    update_after = await client.patch(
        f"/api/v1/tasks/{task_id}",
        headers=owner_hdr,
        json={"title": "Successfully edited after unarchive"},
    )
    assert update_after.status_code == 200


# ============================================================================
# 4. LABEL MANAGEMENT & CONSTRAINTS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_label_assignment_duplicate_and_cross_project(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    owner_hdr = setup_env["owner_hdr"]

    # Create another project
    other_proj_resp = await client.post(
        f"/api/v1/workspaces/{setup_env['workspace']['id']}/projects",
        headers=owner_hdr,
        json={"name": "Frontend Web"},
    )
    other_project_id = other_proj_resp.json()["id"]

    # Create label in other project
    other_label_resp = await client.post(
        f"/api/v1/projects/{other_project_id}/labels",
        headers=owner_hdr,
        json={"name": "Frontend Bug", "color": "#00ff00"},
    )
    other_label_id = other_label_resp.json()["id"]

    # Create label in main project
    label_resp = await client.post(
        f"/api/v1/projects/{project_id}/labels",
        headers=owner_hdr,
        json={"name": "Backend Bug", "color": "#ff0000"},
    )
    label_id = label_resp.json()["id"]

    # Create task in main project
    task_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Label test task"},
    )
    task_id = task_resp.json()["id"]

    # Attaching label from another project -> 422
    cross_assign = await client.post(
        f"/api/v1/tasks/{task_id}/labels/{other_label_id}",
        headers=owner_hdr,
    )
    assert cross_assign.status_code == 422

    # Attach label successfully -> 200
    attach_first = await client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=owner_hdr,
    )
    assert attach_first.status_code == 200

    # Attach DUPLICATE label -> 409
    attach_duplicate = await client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=owner_hdr,
    )
    assert attach_duplicate.status_code == 409

    # Detach label -> 204
    detach_resp = await client.delete(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=owner_hdr,
    )
    assert detach_resp.status_code == 204

    # Detach unattached label -> 404
    detach_again = await client.delete(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=owner_hdr,
    )
    assert detach_again.status_code == 404


# ============================================================================
# 5. COMMENT PERMISSIONS & MANAGEMENT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_comment_edit_and_delete_permissions(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    owner_hdr = setup_env["owner_hdr"]
    editor_hdr = setup_env["editor_hdr"]
    viewer_hdr = setup_env["viewer_hdr"]
    admin_hdr = setup_env["admin_hdr"]

    # Create task
    task_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Discussion Task"},
    )
    task_id = task_resp.json()["id"]

    # Editor posts a comment
    comment_resp = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=editor_hdr,
        json={"content": "Editor's initial opinion"},
    )
    assert comment_resp.status_code == 201
    comment_id = comment_resp.json()["id"]

    # Viewer cannot edit or delete -> 403
    viewer_edit = await client.patch(
        f"/api/v1/comments/{comment_id}",
        headers=viewer_hdr,
        json={"content": "Viewer trying to edit"},
    )
    assert viewer_edit.status_code == 403

    # Another editor (or user) cannot edit/delete another person's comment:
    # Register another editor in the workspace
    other_editor = await register_user(client, "editor2@example.com", "Second Editor")
    await client.post(
        f"/api/v1/workspaces/{setup_env['workspace']['id']}/members",
        headers=owner_hdr,
        json={"user_id": other_editor["id"], "role": WorkspaceRole.EDITOR.value},
    )
    other_editor_hdr = await login_user(client, "editor2@example.com")

    # Second editor tries to delete first editor's comment -> 403
    other_delete = await client.delete(
        f"/api/v1/comments/{comment_id}",
        headers=other_editor_hdr,
    )
    assert other_delete.status_code == 403

    # Author can edit their own comment -> 200
    author_edit = await client.patch(
        f"/api/v1/comments/{comment_id}",
        headers=editor_hdr,
        json={"content": "Editor revised this comment"},
    )
    assert author_edit.status_code == 200
    assert author_edit.json()["content"] == "Editor revised this comment"

    # Workspace OWNER can delete any member's comment -> 204
    owner_delete = await client.delete(
        f"/api/v1/comments/{comment_id}",
        headers=owner_hdr,
    )
    assert owner_delete.status_code == 204

    # Post another comment to test Admin delete
    comment2 = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=editor_hdr,
        json={"content": "Comment for admin test"},
    )
    comment2_id = comment2.json()["id"]

    # System ADMIN can delete comment -> 204
    admin_delete = await client.delete(
        f"/api/v1/comments/{comment2_id}",
        headers=admin_hdr,
    )
    assert admin_delete.status_code == 204


# ============================================================================
# 6. FILTERING & PAGINATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_task_filtering_and_pagination(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    owner_hdr = setup_env["owner_hdr"]
    editor_id = setup_env["editor"]["id"]
    owner_id = setup_env["owner"]["id"]

    # Create 5 tasks with varied statuses and priorities
    # Task 1: TODO, LOW, assigned to owner
    await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={
            "title": "Task 1",
            "priority": TaskPriority.LOW.value,
            "assignee_id": owner_id,
        },
    )
    # Task 2: TODO, HIGH, assigned to editor -> update to IN_PROGRESS
    t2 = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={
            "title": "Task 2",
            "priority": TaskPriority.HIGH.value,
            "assignee_id": editor_id,
        },
    )
    await client.patch(
        f"/api/v1/tasks/{t2.json()['id']}",
        headers=owner_hdr,
        json={"status": TaskStatus.IN_PROGRESS.value},
    )

    # Task 3: TODO, HIGH, assigned to owner -> update to DONE
    t3 = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={
            "title": "Task 3",
            "priority": TaskPriority.HIGH.value,
            "assignee_id": owner_id,
        },
    )
    await client.patch(
        f"/api/v1/tasks/{t3.json()['id']}",
        headers=owner_hdr,
        json={"status": TaskStatus.DONE.value},
    )

    # Task 4: TODO, URGENT, assigned to editor
    await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={
            "title": "Task 4",
            "priority": TaskPriority.URGENT.value,
            "assignee_id": editor_id,
        },
    )

    # Task 5: TODO, LOW, unassigned
    await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Task 5", "priority": TaskPriority.LOW.value},
    )

    # 1. Total tasks should be 5
    all_tasks = await client.get(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
    )
    assert all_tasks.status_code == 200
    data = all_tasks.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5

    # 2. Filter by status: TODO only (Tasks 1, 4, 5)
    todo_tasks = await client.get(
        f"/api/v1/projects/{project_id}/tasks?status=TODO",
        headers=owner_hdr,
    )
    assert todo_tasks.json()["total"] == 3
    assert {t["title"] for t in todo_tasks.json()["items"]} == {
        "Task 1",
        "Task 4",
        "Task 5",
    }

    # 3. Filter by multiple statuses: IN_PROGRESS + DONE
    inprog_done = await client.get(
        f"/api/v1/projects/{project_id}/tasks?status=IN_PROGRESS&status=DONE",
        headers=owner_hdr,
    )
    assert inprog_done.json()["total"] == 2
    assert {t["title"] for t in inprog_done.json()["items"]} == {"Task 2", "Task 3"}

    # 4. Filter by priority: HIGH only
    high_tasks = await client.get(
        f"/api/v1/projects/{project_id}/tasks?priority=HIGH",
        headers=owner_hdr,
    )
    assert high_tasks.json()["total"] == 2
    assert {t["title"] for t in high_tasks.json()["items"]} == {"Task 2", "Task 3"}

    # 5. Filter by assignee: editor
    editor_tasks = await client.get(
        f"/api/v1/projects/{project_id}/tasks?assignee_id={editor_id}",
        headers=owner_hdr,
    )
    assert editor_tasks.json()["total"] == 2
    assert {t["title"] for t in editor_tasks.json()["items"]} == {"Task 2", "Task 4"}

    # 6. Pagination: limit=2, page=1
    p1 = await client.get(
        f"/api/v1/projects/{project_id}/tasks?page=1&limit=2",
        headers=owner_hdr,
    )
    assert p1.json()["total"] == 5
    assert len(p1.json()["items"]) == 2
    assert p1.json()["page"] == 1
    assert p1.json()["limit"] == 2

    # Pagination: limit=2, page=2
    p2 = await client.get(
        f"/api/v1/projects/{project_id}/tasks?page=2&limit=2",
        headers=owner_hdr,
    )
    assert p2.json()["total"] == 5
    assert len(p2.json()["items"]) == 2
    assert p2.json()["page"] == 2


# ============================================================================
# 7. CASCADE DELETE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_cascade_delete_task_and_project(
    client: AsyncClient, setup_env: dict
) -> None:
    project_id = setup_env["project"]["id"]
    owner_hdr = setup_env["owner_hdr"]

    # Create task
    task_resp = await client.post(
        f"/api/v1/projects/{project_id}/tasks",
        headers=owner_hdr,
        json={"title": "Cascade task"},
    )
    task_id = task_resp.json()["id"]

    # Create label and attach to task
    lbl_resp = await client.post(
        f"/api/v1/projects/{project_id}/labels",
        headers=owner_hdr,
        json={"name": "Cascade Label", "color": "#123456"},
    )
    label_id = lbl_resp.json()["id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=owner_hdr,
    )

    # Add comment to task
    await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        headers=owner_hdr,
        json={"content": "Cascade Comment"},
    )

    # Delete task should succeed without 500
    del_task = await client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=owner_hdr,
    )
    assert del_task.status_code == 204

    # Delete project should succeed without 500
    del_proj = await client.delete(
        f"/api/v1/projects/{project_id}",
        headers=owner_hdr,
    )
    assert del_proj.status_code == 204

from fastapi import APIRouter, status

from app.dependencies import (
    CommentContextDep,
    CommentServiceDep,
    CurrentUser,
    PaginationDep,
    TaskContextDep,
)
from app.models.comment import Comment
from app.schemas.base import PaginatedResponse
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate

router = APIRouter()


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    task_ctx: TaskContextDep,
    current_user: CurrentUser,
    payload: CommentCreate,
    service: CommentServiceDep,
) -> Comment:
    task_ctx.check_can_write()
    return await service.create_comment(
        task_id=task_ctx.task.id,
        author_id=current_user.id,
        payload=payload,
    )


@router.get(
    "/tasks/{task_id}/comments",
    response_model=PaginatedResponse[CommentResponse],
)
async def list_task_comments(
    task_ctx: TaskContextDep,
    pagination: PaginationDep,
    service: CommentServiceDep,
) -> PaginatedResponse[CommentResponse]:
    task_ctx.check_can_read()
    return await service.list_comments(task_ctx.task.id, pagination)


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentResponse,
)
async def update_comment(
    comment_ctx: CommentContextDep,
    current_user: CurrentUser,
    payload: CommentUpdate,
    service: CommentServiceDep,
) -> Comment:
    comment_ctx.check_can_delete_or_edit(current_user.id)
    return await service.update_comment(comment_ctx.comment, payload)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    comment_ctx: CommentContextDep,
    current_user: CurrentUser,
    service: CommentServiceDep,
) -> None:
    comment_ctx.check_can_delete_or_edit(current_user.id)
    await service.delete_comment(comment_ctx.comment)

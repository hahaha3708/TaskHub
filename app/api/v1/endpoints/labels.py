from fastapi import APIRouter, status

from app.dependencies import (
    LabelContextDep,
    LabelServiceDep,
    PaginationDep,
    ProjectContextDep,
)
from app.models.label import Label
from app.schemas.base import PaginatedResponse
from app.schemas.label import LabelCreate, LabelResponse, LabelUpdate

router = APIRouter()


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_label(
    project_ctx: ProjectContextDep,
    payload: LabelCreate,
    service: LabelServiceDep,
) -> Label:
    project_ctx.check_can_write()
    return await service.create_label(project_ctx.project.id, payload)


@router.get(
    "/projects/{project_id}/labels",
    response_model=PaginatedResponse[LabelResponse],
)
async def list_project_labels(
    project_ctx: ProjectContextDep,
    pagination: PaginationDep,
    service: LabelServiceDep,
) -> PaginatedResponse[LabelResponse]:
    project_ctx.check_can_read()
    return await service.list_labels(project_ctx.project.id, pagination)


@router.patch(
    "/labels/{label_id}",
    response_model=LabelResponse,
)
async def update_label(
    label_ctx: LabelContextDep,
    payload: LabelUpdate,
    service: LabelServiceDep,
) -> Label:
    label_ctx.check_can_write()
    return await service.update_label(label_ctx.label, payload)


@router.delete(
    "/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_label(
    label_ctx: LabelContextDep,
    service: LabelServiceDep,
) -> None:
    label_ctx.check_can_write()
    await service.delete_label(label_ctx.label)

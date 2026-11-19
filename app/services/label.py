from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label
from app.repositories.label import LabelRepository
from app.schemas.base import PaginatedResponse, PaginationParams
from app.schemas.label import LabelCreate, LabelResponse, LabelUpdate


class LabelService:
    def __init__(
        self, session: AsyncSession, repository: LabelRepository | None = None
    ) -> None:
        self.session = session
        self.repository = repository or LabelRepository(session)

    async def create_label(self, project_id: int, payload: LabelCreate) -> Label:
        label = await self.repository.create(project_id, payload)
        await self.session.commit()
        return label

    async def list_labels(
        self, project_id: int, pagination: PaginationParams
    ) -> PaginatedResponse[LabelResponse]:
        items, total = await self.repository.list_by_project(project_id, pagination)
        return PaginatedResponse[LabelResponse](
            items=[LabelResponse.model_validate(label) for label in items],
            total=total,
            page=pagination.page,
            limit=pagination.limit,
        )

    async def update_label(self, label: Label, payload: LabelUpdate) -> Label:
        updated = await self.repository.update(label, payload)
        await self.session.commit()
        return updated

    async def delete_label(self, label: Label) -> None:
        await self.repository.delete(label)
        await self.session.commit()

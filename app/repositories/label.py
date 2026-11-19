from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label
from app.schemas.base import PaginationParams
from app.schemas.label import LabelCreate, LabelUpdate


class LabelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, label_id: int) -> Label | None:
        return await self.session.get(Label, label_id)

    async def list_by_project(
        self, project_id: int, pagination: PaginationParams
    ) -> tuple[list[Label], int]:
        condition = Label.project_id == project_id
        count_stmt = select(func.count(Label.id)).where(condition)
        total = (await self.session.execute(count_stmt)).scalar_one()

        list_stmt = (
            select(Label)
            .where(condition)
            .order_by(Label.id.asc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        items = list((await self.session.execute(list_stmt)).scalars().all())
        return items, int(total)

    async def create(self, project_id: int, payload: LabelCreate) -> Label:
        label = Label(
            project_id=project_id,
            name=payload.name,
            color=payload.color,
        )
        self.session.add(label)
        await self.session.flush()
        await self.session.refresh(label)
        return label

    async def update(self, label: Label, payload: LabelUpdate) -> Label:
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(label, field, value)
        await self.session.flush()
        await self.session.refresh(label)
        return label

    async def delete(self, label: Label) -> None:
        await self.session.delete(label)
        await self.session.flush()

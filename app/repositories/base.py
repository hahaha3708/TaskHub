from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)
CreateT = TypeVar("CreateT", bound=BaseModel)
UpdateT = TypeVar("UpdateT", bound=BaseModel)


class BaseRepository(Generic[ModelT, CreateT, UpdateT]):
    """Generic async repository with CRUD and offset/limit pagination."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _query(self, *filters: ColumnElement[bool]) -> Select[tuple[ModelT]]:
        statement = select(self.model)
        if filters:
            statement = statement.where(*filters)
        return statement

    async def get(self, entity_id: int) -> ModelT | None:
        return await self.session.get(self.model, entity_id)

    async def list(
        self,
        *filters: ColumnElement[bool],
        offset: int = 0,
        limit: int | None = None,
    ) -> list[ModelT]:
        statement = self._query(*filters).offset(offset)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count(self, *filters: ColumnElement[bool]) -> int:
        statement = select(func.count()).select_from(self._query(*filters).subquery())
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def paginate(
        self,
        *filters: ColumnElement[bool],
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[ModelT], int]:
        offset = (page - 1) * limit
        items = await self.list(*filters, offset=offset, limit=limit)
        total = await self.count(*filters)
        return items, total

    async def create(self, payload: CreateT) -> ModelT:
        entity = self.model(**payload.model_dump())
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT, payload: UpdateT) -> ModelT:
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(entity, field, value)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.commit()

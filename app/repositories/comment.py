from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.schemas.base import PaginationParams
from app.schemas.comment import CommentCreate, CommentUpdate


class CommentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, comment_id: int) -> Comment | None:
        return await self.session.get(Comment, comment_id)

    async def list_by_task(
        self, task_id: int, pagination: PaginationParams
    ) -> tuple[list[Comment], int]:
        condition = Comment.task_id == task_id
        count_stmt = select(func.count(Comment.id)).where(condition)
        total = (await self.session.execute(count_stmt)).scalar_one()

        list_stmt = (
            select(Comment)
            .where(condition)
            .order_by(Comment.created_at.desc(), Comment.id.desc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        items = list((await self.session.execute(list_stmt)).scalars().all())
        return items, int(total)

    async def create(
        self, task_id: int, author_id: int, payload: CommentCreate
    ) -> Comment:
        comment = Comment(
            task_id=task_id,
            author_id=author_id,
            content=payload.content,
        )
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def update(self, comment: Comment, payload: CommentUpdate) -> Comment:
        comment.content = payload.content
        await self.session.flush()
        await self.session.refresh(comment)
        return comment

    async def delete(self, comment: Comment) -> None:
        await self.session.delete(comment)
        await self.session.flush()

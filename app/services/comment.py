from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comment import Comment
from app.repositories.comment import CommentRepository
from app.schemas.base import PaginatedResponse, PaginationParams
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate


class CommentService:
    def __init__(
        self, session: AsyncSession, repository: CommentRepository | None = None
    ) -> None:
        self.session = session
        self.repository = repository or CommentRepository(session)

    async def create_comment(
        self, task_id: int, author_id: int, payload: CommentCreate
    ) -> Comment:
        comment = await self.repository.create(task_id, author_id, payload)
        await self.session.commit()
        return comment

    async def list_comments(
        self, task_id: int, pagination: PaginationParams
    ) -> PaginatedResponse[CommentResponse]:
        items, total = await self.repository.list_by_task(task_id, pagination)
        return PaginatedResponse[CommentResponse](
            items=[CommentResponse.model_validate(c) for c in items],
            total=total,
            page=pagination.page,
            limit=pagination.limit,
        )

    async def update_comment(self, comment: Comment, payload: CommentUpdate) -> Comment:
        updated = await self.repository.update(comment, payload)
        await self.session.commit()
        return updated

    async def delete_comment(self, comment: Comment) -> None:
        await self.repository.delete(comment)
        await self.session.commit()

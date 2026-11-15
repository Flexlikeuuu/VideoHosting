import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_role
from app.core.database import get_db
from app.models.enums import ReportStatus, UserRole
from app.models.user import User
from app.schemas.social import ReportResponse, ResolveReportRequest
from app.services.social import SocialService

router = APIRouter(
    prefix="/moderation",
    tags=["Moderation"],
    dependencies=[Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))],
)


@router.get(
    "/reports",
    response_model=list[ReportResponse],
    summary="Очередь жалоб для модерации",
    description="Доступно только модераторам и администраторам.",
)
async def list_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    status: ReportStatus | None = None,
) -> list[ReportResponse]:
    service = SocialService(db)
    return await service.list_reports(status)


@router.post(
    "/reports/{report_id}/resolve",
    response_model=ReportResponse,
    summary="Рассмотрение жалобы (скрыть видео или отклонить)",
    description="Действие 'hide' скрывает видео (is_hidden=True), 'dismiss' отклоняет жалобу.",
)
async def resolve_report(
    report_id: uuid.UUID,
    req: ResolveReportRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_moderator: Annotated[User, Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))],
) -> ReportResponse:
    service = SocialService(db)
    return await service.resolve_report(report_id, current_moderator, req.action, req.comment)


@router.post(
    "/videos/{video_id}/unhide",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Восстановление скрытого видео (unhide)",
)
async def unhide_video(
    video_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(UserRole.MODERATOR, UserRole.ADMIN))],
) -> None:
    service = SocialService(db)
    await service.unhide_video(video_id)

from __future__ import annotations

from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import ConflictError
from app.application.ports.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        if self._session.in_transaction():
            await self._session.begin_nested()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self._session.rollback()
            return

        try:
            await self._session.commit()
        except IntegrityError as err:
            await self._session.rollback()

            raise ConflictError("commit failed: integrity constraint violated") from err

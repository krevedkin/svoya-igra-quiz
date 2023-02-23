import typing
from hashlib import sha256

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.models import Admin, AdminModel

from app.base.base_accessor import BaseAccessor

if typing.TYPE_CHECKING:
    from app.web.app import Application


class AdminAccessor(BaseAccessor):
    async def connect(self, app: "Application"):
        email = self.app.config.admin.email
        if not await self.get_by_email(email):
            self.app.logger.info("Creating default admin...")

            password = self.app.config.admin.password
            password = sha256(password.encode()).hexdigest()
            await self.create_admin(email=email, password=password)

            self.app.logger.info("Default admin successfully created")
        else:
            self.app.logger.info("Default admin is already created")

    async def disconnect(self, app: "Application"):
        email = self.app.config.admin.email
        admin = await self.get_by_email(email)
        if admin:
            async with self.app.database.session() as session:
                session: AsyncSession
                stmt = delete(AdminModel).where(AdminModel.id == admin.id)
                await session.execute(stmt)
                await session.commit()

    async def get_by_email(self, email: str) -> typing.Optional[Admin]:
        async with self.app.database.session() as session:
            session: AsyncSession
            stmt = select(AdminModel).where(AdminModel.email == email)
            result = await session.scalars(stmt)
            result = result.first()
            if result:
                return Admin(
                    id=result.id,
                    email=result.email,
                    password=result.password,
                )
            return None

    async def create_admin(self, email: str, password: str) -> Admin:
        admin = AdminModel(email=email, password=password)
        async with self.app.database.session() as session:
            session: AsyncSession
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            return Admin(
                id=admin.id,
                email=admin.email,
                password=admin.password,
            )

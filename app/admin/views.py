from dataclasses import asdict

from aiohttp.web import HTTPForbidden
from aiohttp_apispec import request_schema, response_schema, docs
from aiohttp_session import new_session

from app.admin.schemes import (
    AdminSchema,
    AdminLoginRequestSchema,
    AdminLoginResponseSchema,
)
from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response


class AdminLoginView(View):
    @docs(tags=["admin"], summary="admin login endpoint")
    @request_schema(AdminLoginRequestSchema)
    @response_schema(AdminLoginResponseSchema)
    async def post(self):
        admin = await self.request.app.store.admins.get_by_email(
            self.data["email"],
        )
        if not admin:
            raise HTTPForbidden
        if admin.is_password_valid(self.data["password"]):
            session = await new_session(request=self.request)
            session["admin"] = asdict(admin)
        else:
            raise HTTPForbidden
        return json_response(
            status="ok",
            data=AdminLoginResponseSchema().dump(admin),
        )


class AdminCurrentView(AuthRequiredMixin, View):
    @response_schema(AdminSchema, 200)
    async def get(self):
        return json_response(
            status="ok",
            data=AdminLoginResponseSchema().dump(self.request.admin),
        )

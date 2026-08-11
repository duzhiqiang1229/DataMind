"""
Seed script: create initial admin user, roles, permissions, menus.
Fully idempotent — safe to run multiple times.
Run: python -m app.seed_data
"""
import asyncio

from sqlalchemy import select
from app.core.database import async_session, engine, Base
from app.core.security import hash_password
from app.core.config import settings
from app.models import (
    User, Role, Permission, UserRole, Menu, RoleMenu,
    SystemConfig, RolePermission,
)


async def seed():
    async with async_session() as db:
        # --- Create tables (safe if already exist) ---
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Tables verified")

        # --- Admin user ---
        admin_username = settings.INITIAL_ADMIN_USERNAME
        admin_password = settings.INITIAL_ADMIN_PASSWORD or "admin123"
        if settings.APP_ENV.lower() == "production" and len(admin_password) < 12:
            raise RuntimeError("INITIAL_ADMIN_PASSWORD must contain at least 12 characters in production")

        admin_result = await db.execute(select(User).where(User.username == admin_username))
        admin = admin_result.scalar_one_or_none()
        if admin:
            print(f"Admin user already exists (id={admin.id})")
        else:
            admin = User(
                username=admin_username,
                hashed_password=hash_password(admin_password),
                email="admin@datamind.com",
                full_name="System Admin",
                department="IT",
                status="active",
            )
            db.add(admin)
            await db.flush()
            print(f"Admin user created (id={admin.id})")

        # --- Roles (idempotent: fetch or create) ---
        role_map = {}
        for code, name, desc in [
            ("admin", "系统管理员", "拥有全部权限"),
            ("data_engineer", "数据工程师", "数据源/同步/开发管理"),
            ("analyst", "数据分析师", "数据查询与分析"),
            ("viewer", "只读用户", "仅查看权限"),
        ]:
            result = await db.execute(select(Role).where(Role.role_code == code))
            role = result.scalar_one_or_none()
            if role:
                print(f"Role '{code}' already exists, reusing")
            else:
                role = Role(
                    role_code=code,
                    role_name=name,
                    description=desc,
                    status="active",
                )
                db.add(role)
                await db.flush()
                print(f"Role '{code}' created")
            role_map[code] = role

        admin_role = role_map["admin"]

        # --- Assign admin role to admin user (idempotent) ---
        ur_result = await db.execute(
            select(UserRole).where(
                UserRole.user_id == admin.id,
                UserRole.role_id == admin_role.id,
            )
        )
        if not ur_result.scalar_one_or_none():
            db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
            print("Assigned admin role to admin user")
        else:
            print("Admin role already assigned to admin user")

        # --- Permissions (idempotent) ---
        perms_data = [
            ("datasource:view", "查看数据源", "datasource", "view"),
            ("datasource:create", "创建数据源", "datasource", "create"),
            ("datasource:update", "更新数据源", "datasource", "update"),
            ("datasource:delete", "删除数据源", "datasource", "delete"),
            ("datax:task:view", "查看DataX任务", "datax", "view"),
            ("datax:task:create", "创建DataX任务", "datax", "create"),
            ("datax:task:update", "更新DataX任务", "datax", "update"),
            ("datax:task:delete", "删除DataX任务", "datax", "delete"),
            ("datax:task:execute", "执行DataX任务", "datax", "execute"),
            ("doris:query:execute", "执行Doris查询", "doris", "execute"),
            ("doris:query:save", "保存查询", "doris", "create"),
            ("component:view", "查看组件", "component", "view"),
            ("component:manage", "管理组件", "component", "create"),
            ("system:view", "查看系统配置", "system", "view"),
            ("system:manage", "管理系统配置", "system", "create"),
            ("user:view", "查看用户", "user", "view"),
            ("user:create", "创建用户", "user", "create"),
            ("user:update", "更新用户", "user", "update"),
            ("user:delete", "删除用户", "user", "delete"),
            ("role:view", "查看角色", "role", "view"),
            ("role:manage", "管理角色", "role", "create"),
        ]
        perm_ids = []
        permission_map = {}
        for code, name, resource, action in perms_data:
            result = await db.execute(
                select(Permission).where(Permission.permission_code == code)
            )
            p = result.scalar_one_or_none()
            if p:
                pass  # already exists
            else:
                p = Permission(
                    permission_code=code,
                    permission_name=name,
                    resource=resource,
                    action=action,
                )
                db.add(p)
                await db.flush()
            perm_ids.append(p.id)
            permission_map[code] = p

        # --- Assign all permissions to admin role (idempotent) ---
        for pid in perm_ids:
            rp_result = await db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == admin_role.id,
                    RolePermission.permission_id == pid,
                )
            )
            if not rp_result.scalar_one_or_none():
                db.add(RolePermission(role_id=admin_role.id, permission_id=pid))
        print(f"Permissions assigned to admin role ({len(perm_ids)} perms)")

        # Built-in roles get safe defaults. Administrators can still customize
        # these mappings later through role management.
        default_role_permissions = {
            "viewer": {
                "datasource:view", "datax:task:view", "component:view", "system:view",
            },
            "analyst": {
                "datasource:view", "datax:task:view", "component:view", "system:view",
                "doris:query:execute", "doris:query:save",
            },
            "data_engineer": {
                "datasource:view", "datasource:create", "datasource:update", "datasource:delete",
                "datax:task:view", "datax:task:create", "datax:task:update",
                "datax:task:delete", "datax:task:execute", "doris:query:execute",
                "doris:query:save", "component:view", "system:view",
            },
        }
        for role_code, permission_codes in default_role_permissions.items():
            role = role_map[role_code]
            for permission_code in permission_codes:
                permission = permission_map[permission_code]
                rp_result = await db.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == permission.id,
                    )
                )
                if not rp_result.scalar_one_or_none():
                    db.add(RolePermission(role_id=role.id, permission_id=permission.id))

        # --- Menus (idempotent: check by route_path) ---
        menu_data = [
            # (parent_idx, name, type, path, component, icon, sort)
            (None, "首页", "menu", "/dashboard", "dashboard/index", "HomeOutlined", 0),
            (None, "数据管理", "directory", "/datasource", "", "DatabaseOutlined", 1),
            (1, "数据源管理", "menu", "/datasource/list", "datasource/index", "", 0),
            (1, "DataX同步", "menu", "/datax", "datax/index", "", 1),
            (None, "数据开发", "directory", "/dev", "", "CodeOutlined", 2),
            (4, "SQL工作台", "menu", "/query", "query/index", "", 0),
            (4, "数据模型", "menu", "/dev/models", "dev/models/index", "", 1),
            (4, "发布管理", "menu", "/dev/publish", "dev/publish/index", "", 2),
            (None, "数据仓库", "directory", "/warehouse", "", "HddOutlined", 3),
            (8, "库表浏览", "menu", "/warehouse/browse", "warehouse/browse/index", "", 0),
            (None, "调度中心", "directory", "/schedule", "", "ScheduleOutlined", 4),
            (10, "任务监控", "menu", "/schedule/monitor", "schedule/monitor/index", "", 0),
            (None, "数据资产", "directory", "/assets", "", "FundOutlined", 5),
            (12, "数据目录", "menu", "/assets/catalog", "assets/catalog/index", "", 0),
            (12, "血缘关系", "menu", "/assets/lineage", "assets/lineage/index", "", 1),
            (None, "指标中心", "directory", "/metrics", "", "BarChartOutlined", 6),
            (None, "系统管理", "directory", "/system", "", "SettingOutlined", 7),
            (16, "用户管理", "menu", "/system/user", "system/user/index", "", 0),
            (16, "角色管理", "menu", "/system/role", "system/role/index", "", 1),
            (16, "组件配置", "menu", "/system/component", "system/component/index", "", 2),
            (16, "系统配置", "menu", "/system/config", "system/config/index", "", 3),
            (16, "操作日志", "menu", "/system/log", "system/log/index", "", 4),
        ]

        menu_ids = []
        for i, (parent_idx, name, mtype, path, comp, icon, sort) in enumerate(menu_data):
            parent_id = menu_ids[parent_idx] if parent_idx is not None else None
            result = await db.execute(select(Menu).where(Menu.route_path == path))
            m = result.scalar_one_or_none()
            if m:
                pass  # already exists
            else:
                m = Menu(
                    parent_id=parent_id,
                    menu_name=name,
                    menu_type=mtype,
                    route_path=path,
                    component=comp,
                    icon=icon,
                    sort_order=sort,
                    visible=True,
                    status="active",
                )
                db.add(m)
                await db.flush()
            menu_ids.append(m.id)

        # --- Assign all menus to admin role (idempotent) ---
        for mid in menu_ids:
            rm_result = await db.execute(
                select(RoleMenu).where(
                    RoleMenu.role_id == admin_role.id,
                    RoleMenu.menu_id == mid,
                )
            )
            if not rm_result.scalar_one_or_none():
                db.add(RoleMenu(role_id=admin_role.id, menu_id=mid))
        print(f"Menus assigned to admin role ({len(menu_ids)} menus)")

        # --- System configs (already idempotent, keep as-is) ---
        configs = [
            ("platform_name", "DataMind", "string", "平台名称"),
            ("platform_version", "1.0.0", "string", "平台版本"),
            ("default_page_size", "20", "int", "默认分页大小"),
            ("sql_query_timeout", "300", "int", "SQL查询超时(秒)"),
            ("sql_max_rows", "10000", "int", "SQL最大返回行数"),
        ]
        for key, val, ctype, desc in configs:
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.config_key == key)
            )
            if not result.scalar_one_or_none():
                db.add(SystemConfig(
                    config_key=key, config_value=val,
                    config_type=ctype, description=desc, is_editable=True,
                ))

        await db.commit()
        print("\nSeed data complete!")
        print(f"  Admin user: {admin_username}")
        print("  Roles: admin, data_engineer, analyst, viewer")
        print(f"  Permissions: {len(perm_ids)}")
        print(f"  Menus: {len(menu_ids)}")


if __name__ == "__main__":
    asyncio.run(seed())

"""
初始化数据库：创建数据库、表、初始角色和权限
"""

from pathlib import Path
import os
import sys

# 添加项目根目录到路径
# 脚本位于 zquant/scripts/init_db.py
# 需要将项目根目录（包含 zquant 目录的目录）添加到路径，而不是 zquant 目录本身
script_dir = Path(__file__).resolve().parent  # zquant/scripts
zquant_dir = script_dir.parent  # zquant 目录
project_root = zquant_dir.parent  # 项目根目录（包含 zquant 目录的目录）
sys.path.insert(0, str(project_root))

from loguru import logger
import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from zquant.core.security import get_password_hash
from zquant.config import settings, print_config_debug_info
from zquant.database import Base, SessionLocal, engine
from zquant.models.user import Permission, Role, RolePermission, User

# 打印配置调试信息
print_config_debug_info()


def create_database_if_not_exists():
    """如果数据库不存在，则创建它"""
    # 打印实际使用的配置（用于调试）
    logger.info("=" * 60)
    logger.info("数据库配置信息:")
    logger.info(f"  主机: {settings.DB_HOST}")
    logger.info(f"  端口: {settings.DB_PORT}")
    logger.info(f"  用户: {settings.DB_USER}")
    logger.info(f"  数据库: {settings.DB_NAME}")
    logger.info(f"  字符集: {settings.DB_CHARSET}")
    logger.info("=" * 60)

    try:
        # 尝试连接数据库
        test_engine = create_engine(
            f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}?charset={settings.DB_CHARSET}",
            pool_pre_ping=True,
        )
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"数据库 '{settings.DB_NAME}' 已存在")
        return True
    except OperationalError as e:
        error_code = e.orig.args[0] if hasattr(e, "orig") and hasattr(e.orig, "args") else None
        if error_code == 1049:  # Unknown database
            logger.info(f"数据库 '{settings.DB_NAME}' 不存在，正在创建...")
            try:
                # 连接到MySQL服务器（不指定数据库）
                admin_engine = create_engine(
                    f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
                    f"@{settings.DB_HOST}:{settings.DB_PORT}?charset={settings.DB_CHARSET}",
                    pool_pre_ping=True,
                )
                with admin_engine.connect() as conn:
                    # 创建数据库
                    conn.execute(
                        text(
                            f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                        )
                    )
                    conn.commit()
                logger.info(f"数据库 '{settings.DB_NAME}' 创建成功")
                return True
            except Exception as create_error:
                logger.error(f"创建数据库失败: {create_error}")
                logger.error("请手动创建数据库:")
                logger.error(
                    f'  mysql -u {settings.DB_USER} -p -e "CREATE DATABASE {settings.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"'
                )
                return False
        else:
            logger.error(f"数据库连接失败: {e}")
            logger.error("请检查数据库配置:")
            logger.error(f"  主机: {settings.DB_HOST}:{settings.DB_PORT}")
            logger.error(f"  用户: {settings.DB_USER}")
            logger.error(f"  数据库: {settings.DB_NAME}")
            return False
    except Exception as e:
        logger.error(f"检查数据库时出错: {e}")
        return False


def init_database():
    """初始化数据库"""
    logger.info("开始初始化数据库...")

    # 首先检查并创建数据库（如果不存在）
    if not create_database_if_not_exists():
        logger.error("数据库初始化失败：无法创建或连接数据库")
        return False

    try:
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")
    except Exception as e:
        logger.error(f"创建数据库表失败: {e}")
        return False

    db = SessionLocal()
    try:
        # 创建角色
        roles_data = [
            {"name": "admin", "description": "系统管理员"},
            {"name": "researcher", "description": "策略研究员"},
            {"name": "user", "description": "量化平台用户"},
        ]

        for role_data in roles_data:
            role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not role:
                role = Role(**role_data)
                db.add(role)
                logger.info(f"创建角色: {role_data['name']}")

        db.commit()

        # 创建权限
        permissions_data = [
            # 用户管理权限
            {"name": "user:create", "resource": "user", "action": "create", "description": "创建用户"},
            {"name": "user:read", "resource": "user", "action": "read", "description": "查看用户"},
            {"name": "user:update", "resource": "user", "action": "update", "description": "更新用户"},
            {"name": "user:delete", "resource": "user", "action": "delete", "description": "删除用户"},
            # 角色管理权限
            {"name": "role:create", "resource": "role", "action": "create", "description": "创建角色"},
            {"name": "role:read", "resource": "role", "action": "read", "description": "查看角色"},
            {"name": "role:update", "resource": "role", "action": "update", "description": "更新角色"},
            {"name": "role:delete", "resource": "role", "action": "delete", "description": "删除角色"},
            # 权限管理权限
            {"name": "permission:create", "resource": "permission", "action": "create", "description": "创建权限"},
            {"name": "permission:read", "resource": "permission", "action": "read", "description": "查看权限"},
            {"name": "permission:update", "resource": "permission", "action": "update", "description": "更新权限"},
            {"name": "permission:delete", "resource": "permission", "action": "delete", "description": "删除权限"},
            # API密钥管理权限（用户可管理自己的密钥，管理员可管理所有密钥）
            {"name": "apikey:create", "resource": "apikey", "action": "create", "description": "创建API密钥"},
            {"name": "apikey:read", "resource": "apikey", "action": "read", "description": "查看API密钥"},
            {"name": "apikey:delete", "resource": "apikey", "action": "delete", "description": "删除API密钥"},
            # 数据服务权限
            {"name": "data:read", "resource": "data", "action": "read", "description": "查看数据"},
            {"name": "data:sync", "resource": "data", "action": "sync", "description": "同步数据"},
            {"name": "data:write", "resource": "data", "action": "write", "description": "写入数据"},
            # 回测服务权限
            {"name": "backtest:run", "resource": "backtest", "action": "run", "description": "运行回测"},
            {"name": "backtest:read", "resource": "backtest", "action": "read", "description": "查看回测"},
            {"name": "backtest:delete", "resource": "backtest", "action": "delete", "description": "删除回测"},
            # 策略管理权限（未来扩展）
            {"name": "strategy:create", "resource": "strategy", "action": "create", "description": "创建策略"},
            {"name": "strategy:read", "resource": "strategy", "action": "read", "description": "查看策略"},
            {"name": "strategy:update", "resource": "strategy", "action": "update", "description": "更新策略"},
            {"name": "strategy:delete", "resource": "strategy", "action": "delete", "description": "删除策略"},
        ]

        for perm_data in permissions_data:
            perm = db.query(Permission).filter(Permission.name == perm_data["name"]).first()
            if not perm:
                perm = Permission(**perm_data)
                db.add(perm)
                logger.info(f"创建权限: {perm_data['name']}")

        db.commit()

        # 分配权限给角色
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        researcher_role = db.query(Role).filter(Role.name == "researcher").first()
        user_role = db.query(Role).filter(Role.name == "user").first()

        # 管理员拥有所有权限
        all_perms = db.query(Permission).all()
        for perm in all_perms:
            # 检查是否已存在关联
            existing = (
                db.query(RolePermission)
                .filter(RolePermission.role_id == admin_role.id, RolePermission.permission_id == perm.id)
                .first()
            )
            if not existing:
                rp = RolePermission(role_id=admin_role.id, permission_id=perm.id)
                db.add(rp)

        # 研究员拥有数据查看、回测和API密钥管理权限
        researcher_perms = (
            db.query(Permission)
            .filter(
                Permission.name.in_(
                    [
                        "data:read",
                        "backtest:run",
                        "backtest:read",
                        "apikey:create",
                        "apikey:read",
                        "apikey:delete",
                        "strategy:create",
                        "strategy:read",
                        "strategy:update",
                        "strategy:delete",
                    ]
                )
            )
            .all()
        )
        for perm in researcher_perms:
            existing = (
                db.query(RolePermission)
                .filter(RolePermission.role_id == researcher_role.id, RolePermission.permission_id == perm.id)
                .first()
            )
            if not existing:
                rp = RolePermission(role_id=researcher_role.id, permission_id=perm.id)
                db.add(rp)

        # 量化平台用户拥有只读权限（数据查看、回测查看）
        user_perms = (
            db.query(Permission)
            .filter(
                Permission.name.in_(
                    [
                        "data:read",
                        "backtest:read",
                    ]
                )
            )
            .all()
        )
        for perm in user_perms:
            existing = (
                db.query(RolePermission)
                .filter(RolePermission.role_id == user_role.id, RolePermission.permission_id == perm.id)
                .first()
            )
            if not existing:
                rp = RolePermission(role_id=user_role.id, permission_id=perm.id)
                db.add(rp)

        db.commit()
        logger.info("角色权限分配完成")

        # 输出权限分配摘要
        admin_perms_count = db.query(RolePermission).filter(RolePermission.role_id == admin_role.id).count()
        researcher_perms_count = db.query(RolePermission).filter(RolePermission.role_id == researcher_role.id).count()
        user_perms_count = db.query(RolePermission).filter(RolePermission.role_id == user_role.id).count()
        logger.info(f"管理员角色拥有 {admin_perms_count} 个权限")
        logger.info(f"研究员角色拥有 {researcher_perms_count} 个权限")
        logger.info(f"量化平台用户角色拥有 {user_perms_count} 个权限")

        # 创建默认管理员用户
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            admin_user = User(
                username="admin",
                email="admin@zquant.com",
                hashed_password=get_password_hash("admin123"),  # 默认密码，生产环境应修改
                role_id=admin_role.id,
                is_active=True,
            )
            db.add(admin_user)
            db.commit()
            logger.info("创建默认管理员用户: admin / admin123")

        logger.info("数据库初始化完成")
        return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        if "db" in locals():
            db.rollback()
        return False
    finally:
        if "db" in locals():
            db.close()


if __name__ == "__main__":
    success = init_database()
    if not success:
        sys.exit(1)

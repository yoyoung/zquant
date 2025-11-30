#!/usr/bin/env python3

# 导入LogWrapper
import os

from instock.lib.log_wrapper import _loginstance
import numpy as np
import pandas as pd
import pymysql
from sqlalchemy import create_engine, inspect
from sqlalchemy.types import NVARCHAR

__author__ = "myh "
__date__ = "2023/3/10 "

logger = _loginstance.get_logger(__name__)

db_host = "localhost"  # 数据库服务主机
db_user = "root"  # 数据库访问用户
db_password = ""  # 数据库访问密码
db_database = "instockdb_tushare"  # 数据库名称
# db_database = "instockdb"  # 数据库名称
db_port = 3307  # 数据库服务端口
db_charset = "utf8mb4"  # 数据库字符集

# 使用环境变量获得数据库,docker -e 传递
_db_host = os.environ.get("db_host")
if _db_host is not None:
    db_host = _db_host
_db_user = os.environ.get("db_user")
if _db_user is not None:
    db_user = _db_user
_db_password = os.environ.get("db_password")
if _db_password is not None:
    db_password = _db_password
_db_database = os.environ.get("db_database")
if _db_database is not None:
    db_database = _db_database
_db_port = os.environ.get("db_port")
if _db_port is not None:
    db_port = int(_db_port)

MYSQL_CONN_URL = "mysql+pymysql://%s:%s@%s:%s/%s?charset=%s" % (
    db_user,
    db_password,
    db_host,
    db_port,
    db_database,
    db_charset,
)
logger.info(f"数据库链接信息：{MYSQL_CONN_URL}")

MYSQL_CONN_DBAPI = {
    "host": db_host,
    "user": db_user,
    "password": db_password,
    "database": db_database,
    "charset": db_charset,
    "port": db_port,
    "autocommit": True,
}

MYSQL_CONN_TORNDB = {
    "host": f"{db_host}:{db_port!s}",
    "user": db_user,
    "password": db_password,
    "database": db_database,
    "charset": db_charset,
    "max_idle_time": 3600,
    "connect_timeout": 1000,
}


# 通过数据库链接 engine
def engine():
    return create_engine(MYSQL_CONN_URL)


def engine_to_db(to_db):
    _engine = create_engine(MYSQL_CONN_URL.replace(f"/{db_database}?", f"/{to_db}?"))
    return _engine


# DB Api -数据库连接对象connection
def get_connection():
    try:
        connection = pymysql.connect(**MYSQL_CONN_DBAPI)
        if connection is None:
            raise Exception("Failed to create database connection")
        return connection
    except Exception as e:
        logger.error(f"database.get_connection处理异常：{MYSQL_CONN_DBAPI}{e}")
        raise


# 定义通用方法函数，插入数据库表，并创建数据库主键，保证重跑数据的时候索引唯一。
def insert_db_from_df(data, table_name, cols_type, write_index, primary_keys, indexs=None):
    # 插入默认的数据库。
    # 统一将nan替换为None，防止nan写入MySQL
    data = data.where(pd.notnull(data), None)

    # 额外的安全检查：确保没有nan值
    for col in data.columns:
        if data[col].dtype in ["float64", "float32"]:
            # 检查是否有无穷大值
            if np.isinf(data[col]).any():
                logger.warning(f"列 {col} 包含无穷大值，替换为None")
                data[col] = data[col].replace([np.inf, -np.inf], None)
            # 检查是否有nan值
            if data[col].isna().any():
                logger.warning(f"列 {col} 包含nan值，替换为None")
                data[col] = data[col].where(pd.notnull(data[col]), None)

    # 最终检查：确保没有nan值
    if data.isna().any().any():
        logger.error(f"数据中仍存在nan值，列: {data.columns[data.isna().any()].tolist()}")
        # 强制替换所有剩余的nan值
        data = data.where(pd.notnull(data), None)

    insert_other_db_from_df(None, data, table_name, cols_type, write_index, primary_keys, indexs)


# 增加一个插入到其他数据库的方法。
def insert_other_db_from_df(to_db, data, table_name, cols_type, write_index, primary_keys, indexs=None):
    # 定义engine
    if to_db is None:
        engine_mysql = engine()
    else:
        engine_mysql = engine_to_db(to_db)

    # 统一将nan替换为None，防止nan写入MySQL
    data = data.where(pd.notnull(data), None)

    # 额外的安全检查：确保没有nan值
    for col in data.columns:
        if data[col].dtype in ["float64", "float32"]:
            # 检查是否有无穷大值
            if np.isinf(data[col]).any():
                logger.warning(f"列 {col} 包含无穷大值，替换为None")
                data[col] = data[col].replace([np.inf, -np.inf], None)
            # 检查是否有nan值
            if data[col].isna().any():
                logger.warning(f"列 {col} 包含nan值，替换为None")
                data[col] = data[col].where(pd.notnull(data[col]), None)

    # 最终检查：确保没有nan值
    if data.isna().any().any():
        logger.error(f"数据中仍存在nan值，列: {data.columns[data.isna().any()].tolist()}")
        # 强制替换所有剩余的nan值
        data = data.where(pd.notnull(data), None)

    # 使用 http://docs.sqlalchemy.org/en/latest/core/reflection.html
    # 使用检查检查数据库表是否有主键。
    ipt = inspect(engine_mysql)
    col_name_list = data.columns.tolist()
    # 如果有索引，把索引增加到varchar上面。
    if write_index:
        # 插入到第一个位置：
        col_name_list.insert(0, data.index.name)

    try:
        if cols_type is None:
            data.to_sql(
                name=table_name,
                con=engine_mysql,
                schema=to_db,
                if_exists="append",
                index=write_index,
            )
        elif not cols_type:
            data.to_sql(
                name=table_name,
                con=engine_mysql,
                schema=to_db,
                if_exists="append",
                dtype={col_name: NVARCHAR(255) for col_name in col_name_list},
                index=write_index,
            )
        else:
            data.to_sql(
                name=table_name,
                con=engine_mysql,
                schema=to_db,
                if_exists="append",
                dtype=cols_type,
                index=write_index,
            )
    except Exception as e:
        logger.error(f"database.insert_other_db_from_df处理异常：{table_name}表{e}")
        raise

    # 检查表是否存在主键，如果不存在则添加主键和索引
    try:
        # 检查表是否存在
        if ipt.has_table(table_name):
            # 检查主键是否存在
            pk_constraint = ipt.get_pk_constraint(table_name)
            if not pk_constraint["constrained_columns"] and primary_keys is not None and primary_keys.strip():
                # 执行数据库插入数据。
                with get_connection() as conn, conn.cursor() as db:
                    db.execute(f"ALTER TABLE `{table_name}` ADD PRIMARY KEY ({primary_keys});")
                    if indexs is not None:
                        for k in indexs:
                            db.execute(f"ALTER TABLE `{table_name}` ADD INDEX IN{k}({indexs[k]});")
        else:
            logger.warning(f"表 {table_name} 不存在，无法添加主键和索引")
    except Exception as e:
        logger.error(f"database.insert_other_db_from_df处理异常：{table_name}表{e}")


# 更新数据
def update_db_from_df(data, table_name, where):
    data = data.where(data.notnull(), None)

    # 额外的安全检查：确保没有nan值
    for col in data.columns:
        if data[col].dtype in ["float64", "float32"]:
            # 检查是否有无穷大值
            if np.isinf(data[col]).any():
                logger.warning(f"列 {col} 包含无穷大值，替换为None")
                data[col] = data[col].replace([np.inf, -np.inf], None)
            # 检查是否有nan值
            if data[col].isna().any():
                logger.warning(f"列 {col} 包含nan值，替换为None")
                data[col] = data[col].where(pd.notnull(data[col]), None)

    # 最终检查：确保没有nan值
    if data.isna().any().any():
        logger.error(f"数据中仍存在nan值，列: {data.columns[data.isna().any()].tolist()}")
        # 强制替换所有剩余的nan值
        data = data.where(pd.notnull(data), None)

    update_string = f"UPDATE `{table_name}` set "
    where_string = " where "
    cols = tuple(data.columns)
    with get_connection() as conn, conn.cursor() as db:
        try:
            for row in data.values:
                sql = update_string
                sql_where = where_string
                for index, col in enumerate(cols):
                    if col in where:
                        if len(sql_where) == len(where_string):
                            if type(row[index]) == str:
                                sql_where = f"""{sql_where}`{col}` = '{row[index]}' """
                            else:
                                sql_where = f"""{sql_where}`{col}` = {row[index]} """
                        elif type(row[index]) == str:
                            sql_where = f"""{sql_where} and `{col}` = '{row[index]}' """
                        else:
                            sql_where = f"""{sql_where} and `{col}` = {row[index]} """
                    elif type(row[index]) == str:
                        if row[index] is None or row[index] != row[index]:
                            sql = f"""{sql}`{col}` = NULL, """
                        else:
                            sql = f"""{sql}`{col}` = '{row[index]}', """
                    elif row[index] is None or row[index] != row[index]:
                        sql = f"""{sql}`{col}` = NULL, """
                    else:
                        sql = f"""{sql}`{col}` = {row[index]}, """
                sql = f"{sql[:-2]}{sql_where}"
                db.execute(sql)
        except Exception as e:
            logger.error(f"database.update_db_from_df处理异常：{sql}{e}")


# 检查表是否存在
def checkTableIsExist(tableName, dbName=None):
    try:
        if dbName is None:
            dbName = MYSQL_CONN_DBAPI["database"]  # 使用当前连接串的库名
        with get_connection() as conn, conn.cursor() as db:
            db.execute(
                """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_name = %s AND table_schema = %s
                    """,
                (tableName, dbName),
            )
            result = db.fetchone()
            if result is not None and result[0] == 1:
                return True
    except Exception as e:
        logger.error(f"database.checkTableIsExist处理异常：{tableName} in {dbName} - {e}")
        return False
    return False


# 增删改数据
def executeSql(sql, params=()):
    with get_connection() as conn, conn.cursor() as db:
        try:
            result = db.execute(sql, params)
            logger.debug(f"Successfully executed SQL: {sql} with params: {params}")
            return result
        except Exception as e:
            logger.error(f"database.executeSql处理异常：{sql} with params: {params} - {e}")
            # 重新抛出异常，让调用者知道操作失败
            raise


# 查询数据
def executeSqlFetch(sql, params=()):
    try:
        with get_connection() as conn, conn.cursor() as db:
            try:
                db.execute(sql, params)
                result = db.fetchall()
                logger.debug(f"Successfully executed SQL query: {sql} with params: {params}")
                return result
            except Exception as e:
                logger.error(f"database.executeSqlFetch处理异常：{sql} with params: {params} - {e}")
                raise
    except Exception as e:
        logger.error(f"database.executeSqlFetch连接异常：{e}")
        raise


# 查询数据并返回字典格式
def executeSqlFetchDict(sql, params=()):
    try:
        with get_connection() as conn, conn.cursor(pymysql.cursors.DictCursor) as db:
            try:
                db.execute(sql, params)
                result = db.fetchall()
                logger.debug(f"Successfully executed SQL query: {sql} with params: {params}")
                return result
            except Exception as e:
                logger.error(f"database.executeSqlFetchDict处理异常：{sql} with params: {params} - {e}")
                raise
    except Exception as e:
        logger.error(f"database.executeSqlFetchDict连接异常：{e}")
        raise


# 计算数量
def executeSqlCount(sql, params=()):
    with get_connection() as conn, conn.cursor() as db:
        try:
            db.execute(sql, params)
            result = db.fetchall()
            if len(result) == 1:
                return int(result[0][0])
            return 0
        except Exception as e:
            logger.error(f"database.select_count计算数量处理异常：{e}")
    return 0


def get_table_columns(table_name: str, db_name: str = None) -> list:
    """
    获取表的列名列表
    Args:
        table_name: 表名
        db_name: 数据库名，如果为None则使用当前连接的数据库
    Returns:
        list: 列名列表，失败返回空列表
    """
    try:
        if db_name is None:
            db_name = MYSQL_CONN_DBAPI["database"]

        with get_connection() as conn, conn.cursor() as db:
            # 使用SHOW COLUMNS获取表结构
            sql = f"SHOW COLUMNS FROM `{table_name}`"
            db.execute(sql)
            result = db.fetchall()

            if result:
                # 第一列是列名
                columns = [row[0] for row in result if row[0]]
                logger.debug(f"Successfully got columns for table {table_name}: {columns}")
                return columns
            logger.warning(f"No columns found for table {table_name}")
            return []

    except Exception as e:
        logger.error(f"database.get_table_columns处理异常：{table_name} in {db_name} - {e}")
        return []


def get_table_columns_detail(table_name: str, db_name: str = None) -> dict:
    """
    获取表的详细列信息
    Args:
        table_name: 表名
        db_name: 数据库名，如果为None则使用当前连接的数据库
    Returns:
        dict: 列信息字典，格式：{'column_name': 'column_type'}，失败返回空字典
    """
    try:
        if db_name is None:
            db_name = MYSQL_CONN_DBAPI["database"]

        with get_connection() as conn, conn.cursor() as db:
            # 使用DESCRIBE获取表结构
            sql = f"DESCRIBE `{table_name}`"
            db.execute(sql)
            result = db.fetchall()

            if result:
                columns = {}
                for row in result:
                    if len(row) >= 2:
                        columns[row[0]] = row[1]  # column_name -> column_type
                logger.debug(f"Successfully got column details for table {table_name}: {list(columns.keys())}")
                return columns
            logger.warning(f"No column details found for table {table_name}")
            return {}

    except Exception as e:
        logger.error(f"database.get_table_columns_detail处理异常：{table_name} in {db_name} - {e}")
        return {}


def convert_sqlalchemy_type_to_mysql(sqlalchemy_type) -> str:
    """
    将SQLAlchemy类型转换为MySQL类型字符串
    Args:
        sqlalchemy_type: SQLAlchemy类型对象
    Returns:
        str: MySQL类型字符串
    """
    try:
        # 获取类型名称
        type_name = str(sqlalchemy_type).upper()

        # 类型映射
        type_mapping = {
            "DOUBLE": "DOUBLE",  # DOUBLE类型（8字节浮点数，精度更高）
            "FLOAT": "FLOAT",  # FLOAT类型（4字节浮点数）
            "INT": "INT",
            "INTEGER": "INT",
            "VARCHAR": str(sqlalchemy_type),  # VARCHAR(6) 等保持原样
            "DATE": "DATE",
            "DATETIME": "DATETIME",
            "TEXT": "TEXT",
            "BOOLEAN": "BOOLEAN",
            "DECIMAL": str(sqlalchemy_type),  # DECIMAL(10,2) 等保持原样
            "BIGINT": "BIGINT",
            "SMALLINT": "SMALLINT",
            "TINYINT": "TINYINT",
            "CHAR": str(sqlalchemy_type),  # CHAR(1) 等保持原样
            "LONGTEXT": "LONGTEXT",
            "MEDIUMTEXT": "MEDIUMTEXT",
            "TIMESTAMP": "TIMESTAMP",
            "TIME": "TIME",
            "YEAR": "YEAR",
            "BLOB": "BLOB",
            "LONGBLOB": "LONGBLOB",
            "MEDIUMBLOB": "MEDIUMBLOB",
            "TINYBLOB": "TINYBLOB",
        }

        # 处理VARCHAR类型
        if "VARCHAR" in type_name:
            return str(sqlalchemy_type)

        # 处理DECIMAL类型
        if "DECIMAL" in type_name:
            return str(sqlalchemy_type)

        # 处理CHAR类型
        if "CHAR" in type_name and "VARCHAR" not in type_name:
            return str(sqlalchemy_type)

        # 处理基本类型
        for sqlalchemy_pattern, mysql_type in type_mapping.items():
            if sqlalchemy_pattern in type_name:
                return mysql_type

        # 默认返回DOUBLE（日线数据已全部使用DOUBLE类型）
        logger.warning(f"Unknown SQLAlchemy type: {sqlalchemy_type}, using DOUBLE as default")
        return "DOUBLE"

    except Exception as e:
        logger.error(f"Type conversion failed: {e!s}")
        return "DOUBLE"  # 默认返回DOUBLE（日线数据已全部使用DOUBLE类型）


def add_column_to_table(table_name: str, column_name: str, column_definition: str, db_name: str = None) -> bool:
    """
    向表中添加列
    Args:
        table_name: 表名
        column_name: 列名
        column_definition: 列定义（如：FLOAT COMMENT "注释"）
        db_name: 数据库名，如果为None则使用当前连接的数据库
    Returns:
        bool: 添加是否成功
    """
    try:
        if db_name is None:
            db_name = MYSQL_CONN_DBAPI["database"]

        with get_connection() as conn, conn.cursor() as db:
            # 构建ALTER TABLE语句
            sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {column_definition}"

            # 执行SQL
            db.execute(sql)
            logger.info(f"Successfully added column {column_name} to table {table_name}")
            return True

    except Exception as e:
        logger.error(f"database.add_column_to_table处理异常：{table_name} - {column_name} - {e}")
        # 尝试使用更兼容的语法
        try:
            # 简化列定义，去掉COMMENT
            simple_definition = column_definition.split("COMMENT")[0].strip()
            sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {simple_definition}"

            with get_connection() as conn, conn.cursor() as db:
                db.execute(sql)
                logger.info(f"Successfully added column {column_name} to table {table_name} (simplified definition)")
                return True

        except Exception as e2:
            logger.error(f"database.add_column_to_table简化语法也失败：{table_name} - {column_name} - {e2}")
            return False

    return False


def ensure_columns_exist(table_name: str, required_columns: dict, db_name: str = None) -> bool:
    """
    确保表中包含必要的列，如果不存在则自动添加
    Args:
        table_name: 表名
        required_columns: 需要检查的列字典，格式：{'column_name': 'column_definition'}
        db_name: 数据库名，如果为None则使用当前连接的数据库
    Returns:
        bool: 操作是否成功
    """
    try:
        if db_name is None:
            db_name = MYSQL_CONN_DBAPI["database"]

        # 获取表的现有列
        existing_columns = get_table_columns(table_name, db_name)
        if not existing_columns:
            logger.warning(f"无法获取表{table_name}的列信息，跳过列检查")
            return False

        # 检查并添加缺失的列
        success_count = 0
        total_required = len(required_columns)

        for column_name, column_definition in required_columns.items():
            if column_name not in existing_columns:
                logger.info(f"表{table_name}缺少列{column_name}，正在添加...")
                if add_column_to_table(table_name, column_name, column_definition, db_name):
                    success_count += 1
                    logger.info(f"成功添加列{column_name}到表{table_name}")
                else:
                    logger.error(f"添加列{column_name}到表{table_name}失败")
            else:
                logger.debug(f"表{table_name}已包含列{column_name}")
                success_count += 1

        if success_count == total_required:
            logger.info(f"表{table_name}列检查完成，所有必要列都已存在或添加成功")
            return True
        logger.warning(f"表{table_name}列检查完成，成功处理{success_count}/{total_required}个列")
        return False

    except Exception as e:
        logger.error(f"database.ensure_columns_exist处理异常：{table_name} - {e}")
        return False


def ensure_columns_exist_with_sqlalchemy(table_name: str, column_definitions: dict, db_name: str = None) -> bool:
    """
    确保表中包含必要的列，支持SQLAlchemy类型定义
    Args:
        table_name: 表名
        column_definitions: 列定义字典，格式：{'column_name': {'type': sqlalchemy_type, 'cn': 'comment'}}
        db_name: 数据库名，如果为None则使用当前连接的数据库
    Returns:
        bool: 操作是否成功
    """
    try:
        if db_name is None:
            db_name = MYSQL_CONN_DBAPI["database"]

        # 获取表的现有列
        existing_columns = get_table_columns_detail(table_name, db_name)
        if not existing_columns:
            logger.warning(f"无法获取表{table_name}的列信息，跳过列检查")
            return False

        # 检查并添加缺失的列
        success_count = 0
        total_required = len(column_definitions)

        for column_name, column_def in column_definitions.items():
            if column_name not in existing_columns:
                logger.info(f"表{table_name}缺少列{column_name}，正在添加...")

                # 转换SQLAlchemy类型为MySQL类型
                sqlalchemy_type = column_def.get("type")
                comment = column_def.get("cn", "")

                if sqlalchemy_type is None:
                    logger.error(f"列{column_name}缺少type定义")
                    continue

                mysql_type = convert_sqlalchemy_type_to_mysql(sqlalchemy_type)

                # 构建列定义
                column_definition = mysql_type
                if comment:
                    column_definition += f" COMMENT '{comment}'"

                if add_column_to_table(table_name, column_name, column_definition, db_name):
                    success_count += 1
                    logger.info(f"成功添加列{column_name}到表{table_name}")
                else:
                    logger.error(f"添加列{column_name}到表{table_name}失败")
            else:
                logger.debug(f"表{table_name}已包含列{column_name}")
                success_count += 1

        if success_count == total_required:
            logger.info(f"表{table_name}列检查完成，所有必要列都已存在或添加成功")
            return True
        logger.warning(f"表{table_name}列检查完成，成功处理{success_count}/{total_required}个列")
        return False

    except Exception as e:
        logger.error(f"database.ensure_columns_exist_with_sqlalchemy处理异常：{table_name} - {e}")
        return False


def create_table_if_not_exists(table_name: str, table_definition: dict, db_name: str = None) -> bool:
    """
    创建表（如果不存在）并确保所有列都存在
    Args:
        table_name: 表名
        table_definition: 表定义字典，格式：
            {
                'columns': {'column_name': {'type': sqlalchemy_type, 'cn': 'comment'}},
                'primary_keys': ['key1', 'key2'],
                'indexs': {'index_name': 'column_name'}
            }
        db_name: 数据库名，如果为None则使用当前连接的数据库
    Returns:
        bool: 操作是否成功
    """
    try:
        if db_name is None:
            db_name = MYSQL_CONN_DBAPI["database"]

        # 检查表是否存在
        if checkTableIsExist(table_name, db_name):
            # 表存在，检查是否需要添加新列
            logger.info(f"表{table_name}已存在，检查列结构...")
            return ensure_columns_exist_with_sqlalchemy(table_name, table_definition["columns"], db_name)

        # 表不存在，创建新表
        logger.info(f"表{table_name}不存在，开始创建...")

        # 构建CREATE TABLE语句
        columns_sql = []
        for column_name, column_def in table_definition["columns"].items():
            sqlalchemy_type = column_def.get("type")
            comment = column_def.get("cn", "")
            auto_increment = column_def.get("auto_increment", False)

            if sqlalchemy_type is None:
                logger.error(f"列{column_name}缺少type定义")
                continue

            mysql_type = convert_sqlalchemy_type_to_mysql(sqlalchemy_type)
            column_sql = f"`{column_name}` {mysql_type}"

            # 添加自增属性
            if auto_increment:
                column_sql += " AUTO_INCREMENT"

            if comment:
                column_sql += f" COMMENT '{comment}'"
            columns_sql.append(column_sql)

        if not columns_sql:
            logger.error(f"表{table_name}没有有效的列定义")
            return False

        # 构建主键
        primary_keys_sql = ""
        if table_definition.get("primary_keys"):
            primary_keys = [f"`{key}`" for key in table_definition["primary_keys"]]
            primary_keys_sql = f", PRIMARY KEY ({', '.join(primary_keys)})"

        # 构建索引
        indexes_sql = ""
        if table_definition.get("indexs"):
            for index_name, column_name in table_definition["indexs"].items():
                # 处理复合索引（用逗号分隔的列名）
                if "," in column_name:
                    # 复合索引，需要处理列名
                    columns = [col.strip() for col in column_name.split(",")]
                    column_list = ", ".join([f"`{col}`" for col in columns])
                else:
                    # 单列索引
                    column_list = f"`{column_name}`"
                indexes_sql += f", INDEX `{index_name}` ({column_list})"

        # 执行CREATE TABLE语句
        create_sql = f"""
            CREATE TABLE `{table_name}` (
                {", ".join(columns_sql)}
                {primary_keys_sql}
                {indexes_sql}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """

        with get_connection() as conn, conn.cursor() as db:
            db.execute(create_sql)
            logger.info(f"成功创建表{table_name}")
            return True

    except Exception as e:
        logger.error(f"database.create_table_if_not_exists处理异常：{table_name} - {e}")
        return False


def create_table_if_not_exists_from_template(table_name: str, template_definition: dict, db_name: str = None) -> bool:
    """
    根据模板定义创建表（如果不存在）并确保所有列都存在
    Args:
        table_name: 表名
        template_definition: 模板定义字典，格式：
            {
                'name': 'template_name',
                'columns': {'column_name': {'type': sqlalchemy_type, 'cn': 'comment'}},
                'primary_keys': ['key1', 'key2'],
                'indexs': {'index_name': 'column_name'}
            }
        db_name: 数据库名，如果为None则使用当前连接的数据库
    Returns:
        bool: 操作是否成功
    """
    try:
        # 复制模板定义并设置表名
        table_definition = template_definition.copy()
        table_definition["name"] = table_name

        return create_table_if_not_exists(table_name, table_definition, db_name)

    except Exception as e:
        logger.error(f"database.create_table_if_not_exists_from_template处理异常：{table_name} - {e}")
        return False

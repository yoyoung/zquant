# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: kevin
# Contact:
#     - Email: kevin@vip.qq.com
#     - Wechat: zquant2025
#     - Issues: https://github.com/zquant/zquant/issues
#     - Documentation: https://docs.zquant.com
#     - Repository: https://github.com/zquant/zquant

"""
数据库查询优化工具

提供查询优化相关的工具函数，包括分页、字段选择、查询缓存等。
"""

from typing import Any, TypeVar
from sqlalchemy.orm import Query, joinedload, selectinload
from sqlalchemy import func

T = TypeVar("T")


def paginate_query(
    query: Query[T], page: int = 1, page_size: int = 20, max_page_size: int = 1000
) -> tuple[Query[T], dict[str, Any]]:
    """
    为查询添加分页

    Args:
        query: SQLAlchemy查询对象
        page: 页码（从1开始）
        page_size: 每页记录数
        max_page_size: 最大每页记录数（防止过大查询）

    Returns:
        (分页后的查询对象, 分页信息字典)

    Raises:
        ValueError: 如果页码或每页记录数无效
    """
    if page < 1:
        raise ValueError("页码必须大于0")
    if page_size < 1:
        raise ValueError("每页记录数必须大于0")
    if page_size > max_page_size:
        raise ValueError(f"每页记录数不能超过{max_page_size}")

    # 计算总数
    total = query.count()

    # 计算分页
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size  # 向上取整

    # 应用分页
    paginated_query = query.offset(offset).limit(page_size)

    pagination_info = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }

    return paginated_query, pagination_info


def optimize_query_with_relationships(
    query: Query[T], relationships: list[str] | None = None, use_joinedload: bool = True
) -> Query[T]:
    """
    优化查询，预加载关联关系（避免N+1查询问题）

    Args:
        query: SQLAlchemy查询对象
        relationships: 需要预加载的关联关系列表
        use_joinedload: 是否使用joinedload（True）还是selectinload（False）

    Returns:
        优化后的查询对象

    使用示例:
        # 预加载用户的角色和权限
        query = optimize_query_with_relationships(
            db.query(User),
            relationships=['roles', 'roles.permissions']
        )
    """
    if not relationships:
        return query

    for rel in relationships:
        if use_joinedload:
            query = query.options(joinedload(rel))
        else:
            query = query.options(selectinload(rel))

    return query


def select_fields(query: Query[T], fields: list[str] | None = None) -> Query[T]:
    """
    选择特定字段（减少数据传输量）

    Args:
        query: SQLAlchemy查询对象
        fields: 需要选择的字段列表，None表示选择所有字段

    Returns:
        优化后的查询对象

    注意：
        此功能需要根据具体模型实现，这里提供基础框架
    """
    if not fields:
        return query

    # 注意：SQLAlchemy的字段选择需要根据具体模型实现
    # 这里只是示例框架，实际使用时需要根据模型动态构建
    # query = query.with_entities(Model.field1, Model.field2, ...)

    return query


def add_date_range_filter(
    query: Query[T], date_field: str, start_date: str | None = None, end_date: str | None = None
) -> Query[T]:
    """
    添加日期范围过滤

    Args:
        query: SQLAlchemy查询对象
        date_field: 日期字段名
        start_date: 开始日期（YYYY-MM-DD格式）
        end_date: 结束日期（YYYY-MM-DD格式）

    Returns:
        添加过滤后的查询对象
    """
    # 注意：这里需要根据具体模型实现
    # 示例：query = query.filter(Model.trade_date >= start_date)
    return query


def get_query_stats(query: Query[T]) -> dict[str, Any]:
    """
    获取查询统计信息（用于性能分析）

    Args:
        query: SQLAlchemy查询对象

    Returns:
        查询统计信息字典
    """
    # 获取查询SQL
    compiled = query.statement.compile(compile_kwargs={"literal_binds": True})
    sql_str = str(compiled)

    # 获取参数
    params = compiled.params

    return {
        "sql": sql_str,
        "params": params,
        "estimated_rows": None,  # 需要数据库特定实现
    }

# 单元测试说明

## 概述

本项目使用 Python 标准库的 `unittest` 框架进行单元测试。

## 测试结构

```
tests/unittest/
├── __init__.py              # 测试模块初始化
├── base.py                   # 测试基类（提供数据库设置等）
├── test_security.py         # 安全模块测试（密码加密、JWT等）
├── test_user_service.py     # 用户服务测试
├── test_notification_service.py  # 通知服务测试
├── test_auth_service.py     # 认证服务测试
└── test_models.py           # 数据模型测试
```

## 运行测试

### 一键运行所有测试

在项目根目录运行：

```bash
python run_tests.py
```

### 运行指定模块的测试

```bash
# 只运行安全模块测试
python run_tests.py -m test_security

# 只运行用户服务测试
python run_tests.py -m test_user_service
```

### 控制输出详细程度

```bash
# 安静模式（只显示结果）
python run_tests.py -v 0

# 正常模式
python run_tests.py -v 1

# 详细模式（默认）
python run_tests.py -v 2
```

### 使用 unittest 直接运行

```bash
# 运行所有测试
python -m unittest discover -s tests/unittest -p "test_*.py"

# 运行指定测试文件
python -m unittest tests.unittest.test_security

# 运行指定测试类
python -m unittest tests.unittest.test_security.TestPasswordSecurity

# 运行指定测试方法
python -m unittest tests.unittest.test_security.TestPasswordSecurity.test_get_password_hash
```

## 测试覆盖范围

### 安全模块 (test_security.py)
- 密码哈希和验证
- 密码强度验证
- JWT Token 创建和解析
- API 密钥生成和验证

### 用户服务 (test_user_service.py)
- 用户创建、查询、更新、删除
- 用户密码重置
- 用户列表查询和筛选
- 用户统计

### 通知服务 (test_notification_service.py)
- 通知创建
- 通知查询和分页
- 通知标记已读
- 通知删除
- 未读数量统计

### 认证服务 (test_auth_service.py)
- 用户认证
- 用户登录
- Token 刷新
- 从 Token 获取用户信息

### 数据模型 (test_models.py)
- 用户模型 CRUD
- 角色模型 CRUD
- 通知模型 CRUD
- 模型关系测试

## 测试基类

`BaseTestCase` 提供了以下功能：

- **数据库设置**: 每个测试使用独立的 SQLite 内存数据库
- **测试用户**: 自动创建测试用户和角色
- **清理机制**: 每个测试后自动清理数据库

## 编写新测试

1. 继承 `BaseTestCase`
2. 使用 `self.db` 访问数据库会话
3. 使用 `self.test_user` 和 `self.test_role` 访问测试数据
4. 使用 `self._create_test_user()` 创建额外的测试用户

示例：

```python
from tests.unittest.base import BaseTestCase

class TestMyService(BaseTestCase):
    def test_my_function(self):
        # 使用 self.db 访问数据库
        # 使用 self.test_user 访问测试用户
        result = my_function(self.db, self.test_user.id)
        self.assertIsNotNone(result)
```

## 注意事项

1. 每个测试方法都会创建新的数据库会话，测试之间相互独立
2. 测试使用 SQLite 内存数据库，不会影响实际数据库
3. 所有测试数据在测试结束后自动清理


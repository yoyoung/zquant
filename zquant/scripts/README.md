# 脚本说明

本目录包含ZQuant系统的各种初始化和管理脚本。

## 重要提示

所有脚本都需要从**项目根目录**运行，脚本会自动处理路径问题。

## 初始化脚本

### init_db.py

初始化数据库脚本，用于：
- 创建数据库（如果不存在）
- 创建所有数据库表
- 创建初始角色（admin, researcher, user）
- 创建权限
- 分配角色权限
- 创建默认管理员用户（admin / admin123）

**使用方法：**
```bash
# 从项目根目录运行
python zquant/scripts/init_db.py
```

**注意事项：**
- 需要先配置数据库连接信息（在环境变量或配置文件中）
- 默认管理员账号：`admin` / `admin123`
- 脚本会自动创建数据库（如果不存在）

### init_scheduler.py

定时任务系统初始化脚本，整合了以下功能：
1. 创建数据库表（`zq_task_scheduled_tasks` 和 `zq_task_task_executions`）
2. 创建示例任务（5个基础示例任务）
3. 创建编排任务示例（3个编排任务示例）
4. 创建ZQuant任务（8个ZQuant数据同步任务）

**使用方法：**
```bash
# 默认：建表+创建ZQuant任务
python zquant/scripts/init_scheduler.py

# 执行所有步骤（表+示例+编排+ZQuant）
python zquant/scripts/init_scheduler.py --all

# 只创建表
python zquant/scripts/init_scheduler.py --tables-only

# 只创建示例任务
python zquant/scripts/init_scheduler.py --examples-only

# 只创建编排任务
python zquant/scripts/init_scheduler.py --workflow-only

# 只创建ZQuant任务
python zquant/scripts/init_scheduler.py --zquant-only

# 强制重新创建（删除已存在的任务）
python zquant/scripts/init_scheduler.py --force
```

### init_view.py

视图初始化脚本，通过存储过程创建和更新日线数据和每日指标数据的联合视图。

**使用方法：**
```bash
# 创建所有视图
python zquant/scripts/init_view.py

# 只创建日线数据视图
python zquant/scripts/init_view.py --daily-only

# 只创建每日指标数据视图
python zquant/scripts/init_view.py --daily-basic-only

# 强制重新创建（删除已存在的视图和存储过程）
python zquant/scripts/init_view.py --force
```

### init_strategies.py

策略模板初始化脚本，将示例策略导入为系统模板策略。

**使用方法：**
```bash
python zquant/scripts/init_strategies.py
```

**功能：**
- 导入内置的8种策略模板
- 包括技术分析、基本面分析和量化策略

## 数据管理脚本

### seed_data.py

填充测试数据脚本，用于：
- 同步股票列表
- 同步交易日历
- 同步部分股票的日线数据

**使用方法：**
```bash
python zquant/scripts/seed_data.py
```

**注意事项：**
- 需要配置Tushare Token才能运行
- 建议在开发环境使用

## 数据库工具脚本

### zquant_dbtool.py

数据库操作工具，用于管理zq_data_tustock相关表的操作。

**使用方法：**
```bash
python zquant/scripts/zquant_dbtool.py
```

## 迁移脚本

### migrate_enum_to_varchar.py

将枚举类型字段迁移为VARCHAR类型的脚本。

**使用方法：**
```bash
python zquant/scripts/migrate_enum_to_varchar.py
```

### migrate_stock_table.py

股票表迁移脚本。

**使用方法：**
```bash
python zquant/scripts/migrate_stock_table.py
```

## 验证脚本

### verify_scheduler_tables.py

验证定时任务相关表是否存在的脚本。

**使用方法：**
```bash
python zquant/scripts/verify_scheduler_tables.py
```

## 初始化顺序建议

建议按以下顺序执行初始化脚本：

1. **init_db.py** - 初始化数据库和基础表
2. **init_scheduler.py** - 初始化定时任务系统
3. **init_view.py** - 创建数据视图
4. **init_strategies.py** - 导入策略模板
5. **seed_data.py** - 填充测试数据（可选，仅开发环境）

## 常见问题

### 1. ModuleNotFoundError: No module named 'zquant'

**原因：** 脚本路径设置不正确。

**解决方案：** 确保从项目根目录运行脚本，脚本会自动处理路径问题。如果仍有问题，检查脚本中的路径设置代码。

### 2. 数据库连接失败

**原因：** 数据库配置不正确或数据库服务未启动。

**解决方案：**
- 检查环境变量或配置文件中的数据库连接信息
- 确保MySQL服务已启动
- 检查数据库用户权限

### 3. 表已存在错误

**原因：** 表已经创建过。

**解决方案：**
- 使用 `--force` 参数强制重新创建（如果脚本支持）
- 或手动删除相关表后重新运行脚本

# 数据库初始化指南

本文档说明ZQuant系统的数据库初始化流程和注意事项。

## 数据库表名规范

ZQuant系统遵循严格的数据库表名规范，所有表名都有明确的前缀：

### 表名前缀规范

- **数据表**：`zq_data_*`
  - 示例：`zq_data_tustock_stockbasic`（股票基础信息）
  - 示例：`zq_data_fundamentals`（财务数据）
  - 示例：`zq_data_tustock_tradecal`（交易日历）
  - 分表：`zq_data_tustock_daily_*`（日线数据，按股票代码分表）
  - 分表：`zq_data_tustock_daily_basic_*`（每日指标数据，按股票代码分表）
  - 分表：`zq_data_tustock_factor_*`（因子数据，按股票代码分表）
  - 分表：`zq_data_tustock_stkfactorpro_*`（专业版因子数据，按股票代码分表）

- **应用表**：`zq_app_*`
  - `zq_app_users` - 用户表
  - `zq_app_roles` - 角色表
  - `zq_app_permissions` - 权限表
  - `zq_app_role_permissions` - 角色权限关联表
  - `zq_app_apikeys` - API密钥表
  - `zq_app_configs` - 配置表
  - `zq_app_notifications` - 通知表

- **回测表**：`zq_backtest_*`
  - `zq_backtest_tasks` - 回测任务表
  - `zq_backtest_strategies` - 策略表
  - `zq_backtest_results` - 回测结果表

- **任务表**：`zq_task_*`
  - `zq_task_scheduled_tasks` - 定时任务表
  - `zq_task_task_executions` - 任务执行记录表

- **统计表**：`zq_stats_*`
  - `zq_stats_apisync` - API接口数据同步日志表
  - `zq_stats_statistics` - 每日数据统计表

- **日志表**：`zq_log_*`（规范定义，当前使用 `zq_stats_apisync`）

## 初始化流程

### 步骤1：初始化数据库和基础表

**脚本**：`zquant/scripts/init_db.py`

**功能**：
- 自动创建数据库（如果不存在）
- 创建所有数据库表
- 创建初始角色（admin, researcher, user）
- 创建权限
- 分配角色权限
- 创建默认管理员用户（admin / admin123）

**使用方法**：
```bash
# 从项目根目录运行
python zquant/scripts/init_db.py
```

**注意事项**：
- 需要先配置数据库连接信息（在环境变量或配置文件中）
- 默认管理员账号：`admin` / `admin123`（首次登录后应修改密码）
- 脚本会自动创建数据库（如果不存在）

### 步骤2：初始化定时任务系统

**脚本**：`zquant/scripts/init_scheduler.py`

**功能**：
- 创建定时任务相关表（`zq_task_scheduled_tasks` 和 `zq_task_task_executions`）
- 创建示例任务（5个基础示例任务）
- 创建编排任务示例（3个编排任务示例）
- 创建ZQuant任务（8个ZQuant数据同步任务）

**使用方法**：
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

### 步骤3：创建数据视图

**脚本**：`zquant/scripts/init_view.py`

**功能**：
- 通过存储过程创建和更新日线数据的联合视图
- 通过存储过程创建和更新每日指标数据的联合视图
- 提供统一查询接口，自动合并分表数据

**使用方法**：
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

**注意事项**：
- 视图依赖于分表数据，建议在同步数据后创建视图
- 视图会自动包含所有分表的数据

### 步骤4：导入策略模板

**脚本**：`zquant/scripts/init_strategies.py`

**功能**：
- 导入内置的8种策略模板
- 包括技术分析、基本面分析和量化策略

**使用方法**：
```bash
python zquant/scripts/init_strategies.py
```

## 完整初始化命令

建议按以下顺序执行初始化脚本：

```bash
# 1. 初始化数据库和基础表
python zquant/scripts/init_db.py

# 2. 初始化定时任务系统
python zquant/scripts/init_scheduler.py

# 3. 创建数据视图
python zquant/scripts/init_view.py

# 4. 导入策略模板
python zquant/scripts/init_strategies.py

# 5. 填充测试数据（可选，仅开发环境）
python zquant/scripts/seed_data.py
```

## 表名变更说明

### 已调整的表名

根据最新的数据库表名规范，以下表名已调整：

1. **财务数据表**：`fundamentals` → `zq_data_fundamentals`
2. **通知表**：`notifications` → `zq_app_notifications`

### 迁移注意事项

如果从旧版本升级，需要注意：

1. **表名变更**：需要手动重命名表或使用迁移脚本
2. **外键引用**：所有外键引用已更新为新的表名
3. **索引和约束**：索引和约束名称已更新

### 外键关系

系统使用以下外键关系：

- `zq_app_users.id` ← `zq_app_apikeys.user_id`
- `zq_app_users.id` ← `zq_backtest_tasks.user_id`
- `zq_app_users.id` ← `zq_backtest_strategies.user_id`
- `zq_app_users.id` ← `zq_app_notifications.user_id`
- `zq_app_roles.id` ← `zq_app_users.role_id`
- `zq_app_roles.id` ← `zq_app_role_permissions.role_id`
- `zq_app_permissions.id` ← `zq_app_role_permissions.permission_id`
- `zq_backtest_strategies.id` ← `zq_backtest_tasks.strategy_id`
- `zq_backtest_tasks.id` ← `zq_backtest_results.task_id`
- `zq_data_tustock_stockbasic.ts_code` ← `zq_data_fundamentals.symbol`

## 数据同步日志汇总

系统实现了分表同步日志汇总功能：

### 功能说明

当数据同步涉及分表时（如日线数据、每日指标数据、因子数据等），系统会自动将多个分表的同步记录汇总为一条日志记录。

### 汇总规则

- **分表识别**：系统自动识别以下分表前缀：
  - `zq_data_tustock_daily_*`
  - `zq_data_tustock_daily_basic_*`
  - `zq_data_tustock_factor_*`
  - `zq_data_tustock_stkfactorpro_*`

- **汇总内容**：
  - 汇总所有分表的 `insert_count`、`update_count`、`delete_count`
  - 汇总操作结果（全部成功→success，全部失败→failed，部分成功→partial_success）
  - 汇总错误信息（最多保留前3个）

- **日志记录**：为每个主表记录一条汇总日志到 `zq_stats_apisync` 表

### 示例

假设同步了3个日线数据分表：
- `zq_data_tustock_daily_000001` - 插入100条，成功
- `zq_data_tustock_daily_000002` - 插入200条，成功
- `zq_data_tustock_daily_000003` - 插入150条，失败

系统会记录1条汇总日志：
- 表名：`zq_data_tustock_daily`
- insert_count：450
- operation_result：`partial_success`
- error_message：包含失败分表的错误信息

## 常见问题

### 1. 脚本运行失败：ModuleNotFoundError

**原因**：路径设置不正确。

**解决方案**：
- 确保从项目根目录运行脚本
- 脚本会自动处理路径问题
- 如果仍有问题，检查脚本中的路径设置代码

### 2. 数据库连接失败

**原因**：数据库配置不正确或数据库服务未启动。

**解决方案**：
- 检查环境变量或配置文件中的数据库连接信息
- 确保MySQL服务已启动
- 检查数据库用户权限

### 3. 表已存在错误

**原因**：表已经创建过。

**解决方案**：
- 使用 `--force` 参数强制重新创建（如果脚本支持）
- 或手动删除相关表后重新运行脚本

### 4. 外键约束错误

**原因**：外键引用的表不存在或表名不正确。

**解决方案**：
- 确保所有表都已创建
- 检查外键引用的表名是否正确
- 按照正确的顺序执行初始化脚本

## 验证初始化

初始化完成后，可以通过以下方式验证：

1. **检查表是否存在**：
   ```sql
   SHOW TABLES LIKE 'zq_%';
   ```

2. **检查角色和权限**：
   ```sql
   SELECT * FROM zq_app_roles;
   SELECT * FROM zq_app_permissions;
   ```

3. **检查默认管理员**：
   ```sql
   SELECT * FROM zq_app_users WHERE username = 'admin';
   ```

4. **检查定时任务**：
   ```sql
   SELECT * FROM zq_task_scheduled_tasks;
   ```

## 相关文档

- [脚本使用说明](../zquant/scripts/README.md)
- [数据库表名规范](../zquant/models/data.py)（代码注释）
- [实现总结](../IMPLEMENTATION.md)


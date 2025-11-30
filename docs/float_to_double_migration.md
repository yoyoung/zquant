# 日线数据Float类型迁移为Double类型

## 变更概述

为了解决MySQL中Float类型精度丢失问题，将日线数据相关的所有Float类型替换为Double类型。

## 变更原因

### Float vs Double 精度对比

- **FLOAT（单精度浮点数）**：
  - 存储空间：4字节
  - 精度：约7位有效数字
  - 范围：-3.402823466E+38 到 -1.175494351E-38，0，以及 1.175494351E-38 到 3.402823466E+38

- **DOUBLE（双精度浮点数）**：
  - 存储空间：8字节
  - 精度：约15-17位有效数字
  - 范围：-1.7976931348623157E+308 到 -2.2250738585072014E-308，0，以及 2.2250738585072014E-308 到 1.7976931348623157E+308

### 为什么使用Double

1. **精度要求**：股票价格、成交量、成交额等数据需要高精度，Float的7位有效数字可能无法满足需求
2. **数据一致性**：Python的float类型本身就是double精度，使用Double可以保证数据在Python和MySQL之间的一致性
3. **计算准确性**：量化分析中的计算（如收益率、指标计算等）需要高精度，Double可以提供更准确的结果

## 涉及的表

以下表的所有Float类型字段都已迁移为Double类型：

1. **日线数据表** (`zq_data_tustock_daily_*`)
   - 字段：`open`, `high`, `low`, `close`, `pre_close`, `change`, `pct_chg`, `vol`, `amount`

2. **每日指标数据表** (`zq_data_tustock_daily_basic_*`)
   - 所有Float字段，包括：`close`, `turnover_rate`, `pe`, `pb`, `ps`, `total_mv`, `circ_mv` 等

3. **因子数据表** (`zq_data_tustock_factor_*`)
   - 所有Float字段，包括价格、成交量、技术指标等

4. **专业版因子数据表** (`zq_data_tustock_stkfactorpro_*`)
   - 所有Float字段，包括价格、成交量、技术指标等

5. **回测结果表** (`zq_backtest_results`)
   - 所有Float字段，包括：`total_return`, `annual_return`, `max_drawdown`, `sharpe_ratio`, `win_rate`, `profit_loss_ratio`, `alpha`, `beta`

### 保持Float类型的字段

以下字段保持Float类型，因为不需要高精度：

- **`zq_stats_apisync.duration_seconds`** - 操作耗时（秒），用于记录操作执行时间，Float精度已足够

## 代码变更

### 1. 模型定义

#### `zquant/models/data.py`
- 导入Double类型：`from sqlalchemy.dialects.mysql import DOUBLE as Double`
- 所有相关函数中的Float替换为Double：
  - `create_tustock_daily_class`
  - `create_tustock_daily_basic_class`
  - `create_tustock_factor_class`
  - `create_tustock_stkfactorpro_class`
- **保持Float的字段**：`DataOperationLog.duration_seconds`（耗时字段不需要高精度）

#### `zquant/models/backtest.py`
- 导入Double类型：`from sqlalchemy.dialects.mysql import DOUBLE as Double`
- `BacktestResult`类中的所有Float字段替换为Double：
  - `total_return`, `annual_return`, `max_drawdown`, `sharpe_ratio`, `win_rate`, `profit_loss_ratio`, `alpha`, `beta`

### 2. 类型转换 (`zquant/data/database.py`)

- 更新 `convert_sqlalchemy_type_to_mysql` 函数，添加DOUBLE类型映射
- 默认类型从FLOAT改为DOUBLE

### 3. Schema定义 (`zquant/schemas/data.py`)

- Python的float类型已经是double精度，无需修改
- Schema中的float类型保持不变（Python的float本身就是double精度）

## 数据库迁移

### 迁移脚本

使用 `zquant/scripts/migrate_float_to_double.py` 脚本进行数据迁移：

```bash
# 预览模式（不实际执行）
python zquant/scripts/migrate_float_to_double.py --dry-run

# 执行迁移
python zquant/scripts/migrate_float_to_double.py
```

### 迁移步骤

1. **备份数据库**（重要！）
2. 运行迁移脚本预览模式，查看将要修改的表和列
3. 确认无误后，运行迁移脚本执行模式
4. 验证数据完整性

### 注意事项

- 迁移过程会修改表结构，对于大表可能需要较长时间
- 建议在业务低峰期执行
- 迁移前务必备份数据库
- 迁移后验证数据精度是否提升

## Alembic迁移

Alembic迁移文件：`zquant/alembic/versions/004_migrate_float_to_double.py`

**注意**：由于日线数据表是动态创建的（按ts_code分表），Alembic迁移文件主要用于记录变更历史。实际的数据迁移应使用 `migrate_float_to_double.py` 脚本。

新创建的表将自动使用DOUBLE类型（已在models/data.py中更新）。

## 兼容性说明

### Python端

- Python的float类型本身就是double精度，无需修改代码
- 现有的Python代码可以无缝使用新的Double类型字段

### 数据库端

- MySQL的DOUBLE类型与FLOAT类型在查询语法上完全兼容
- 现有的SQL查询无需修改
- 需要注意DOUBLE类型占用更多存储空间（8字节 vs 4字节）

### API端

- API返回的数据格式不变
- JSON序列化不受影响
- 客户端代码无需修改

## 性能影响

### 存储空间

- 每个Float字段从4字节增加到8字节
- 对于包含大量Float字段的表，存储空间会增加约一倍
- 考虑到数据精度提升的价值，这个代价是值得的

### 查询性能

- DOUBLE类型的查询性能与FLOAT类型基本相同
- 索引性能不受影响
- 计算性能略有提升（因为精度更高，减少了舍入误差）

## 回滚说明

**不建议回滚**，因为：

1. DOUBLE类型精度更高，回滚到FLOAT可能导致数据精度丢失
2. 迁移过程不可逆（从高精度到低精度会丢失信息）
3. 存储空间增加是可接受的代价

如果确实需要回滚，可以：

1. 从备份恢复数据库
2. 修改代码将Double改回Float
3. 重新运行迁移脚本（需要修改脚本支持反向操作）

## 测试建议

1. **精度测试**：验证数据精度是否提升
2. **功能测试**：确保所有数据查询和计算功能正常
3. **性能测试**：验证查询性能是否受影响
4. **数据完整性测试**：确保迁移后数据完整无误

## 相关文件

- `zquant/models/data.py` - 数据模型定义（日线数据、因子数据等）
- `zquant/models/backtest.py` - 回测模型定义（回测结果表）
- `zquant/data/database.py` - 类型转换函数
- `zquant/scripts/migrate_float_to_double.py` - 迁移脚本
- `zquant/alembic/versions/004_migrate_float_to_double.py` - Alembic迁移文件

## 更新日期

2025-01-29


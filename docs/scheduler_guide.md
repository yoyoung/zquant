# 定时任务系统完整使用指南

## 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [基础功能](#基础功能)
4. [实时进度查看](#实时进度查看)
5. [任务编排](#任务编排)
6. [任务类型](#任务类型)
7. [Cron表达式](#cron表达式)
8. [API接口](#api接口)
9. [最佳实践](#最佳实践)
10. [故障排查](#故障排查)

---

## 概述

ZQuant定时任务系统提供了完整的任务管理功能，支持灵活的调度配置、实时状态监控、完整的执行历史记录、Web界面管理和API接口调用。系统基于APScheduler构建，提供了企业级的任务调度能力。

### 功能特性

- ✅ **灵活的调度方式**
  - 支持Cron表达式调度（精确到秒）
  - 支持间隔调度（固定时间间隔执行）
  - 支持一次性任务和循环任务
- ✅ **任务管理**
  - 可以随时启用/禁用任务
  - 可以手动触发任务执行
  - 支持任务暂停和恢复
- ✅ **实时监控**
  - 实时查看任务执行状态
  - 实时查看执行进度（进度百分比和步骤信息）
  - 自动刷新执行历史
  - 实时更新执行消息
- ✅ **任务编排**（高级功能）
  - 支持串行和并行执行
  - 支持任务依赖关系
  - 支持失败处理策略（继续执行或停止）
  - 树形展示，展开查看子任务
- ✅ **执行历史**
  - 查看任务执行历史和统计信息
  - 支持按时间、状态筛选
  - 查看详细的执行日志和错误信息
- ✅ **Web界面管理**
  - 直观的Web界面配置和管理任务
  - 支持拖拽式任务编排（规划中）
  - 实时监控任务执行状态

---

## 快速开始

### 1. 初始化数据库和示例数据

运行统一的初始化脚本：

```bash
python scripts/init_scheduler.py
```

这个脚本会：
1. 创建数据库表（`zq_task_scheduled_tasks` 和 `zq_task_task_executions`）
2. 创建5个基础示例任务
3. 创建3个编排任务示例

**命令行选项**：
- `--tables-only`: 只创建数据库表
- `--examples-only`: 只创建示例任务
- `--workflow-only`: 只创建编排任务示例
- `--force`: 强制重新创建（删除已存在的任务）

**示例**：
```bash
# 执行所有步骤
python scripts/init_scheduler.py

# 只创建表
python scripts/init_scheduler.py --tables-only

# 只创建示例任务
python scripts/init_scheduler.py --examples-only

# 强制重新创建所有任务
python scripts/init_scheduler.py --force
```

### 2. 启动服务

1. **启动后端服务**：
   ```bash
   uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **启动前端服务**：
   ```bash
   cd web
   npm start
   ```

3. **访问管理页面**：
   - 打开浏览器访问：`http://localhost:8000/admin/scheduler`
   - 需要管理员权限登录

---

## 基础功能

### 任务列表

任务列表显示所有定时任务，包括：
- 任务ID、名称、类型
- 调度方式（Cron表达式或间隔秒数）
- 启用/禁用状态
- 最大重试次数
- 创建时间

**注意**：编排任务的子任务默认不显示在列表中，需要展开编排任务才能查看。

### 创建任务

1. 点击"创建任务"按钮
2. 填写任务信息：
   - **任务名称**：任务的唯一标识
   - **任务类型**：选择任务类型（示例任务、编排任务、数据同步等）
   - **Cron表达式**：如 `0 18 * * *`（每天18:00）
   - **间隔秒数**：如 `3600`（每小时）
   - **任务描述**：可选
   - **任务配置**：JSON格式的配置（根据任务类型不同）
   - **最大重试次数**：任务失败时的重试次数
   - **重试间隔**：重试间隔（秒）
   - **启用任务**：是否立即启用

#### 示例任务配置示例

```json
{
  "duration_seconds": 3,
  "success_rate": 1.0,
  "message": "任务执行完成",
  "steps": 5
}
```

配置说明：
- `duration_seconds`: 模拟执行时长（秒），默认3秒
- `success_rate`: 成功概率（0-1），默认1.0（100%成功）
- `message`: 自定义消息
- `steps`: 处理步骤数量，默认5

### 编辑任务

1. 在任务列表中点击"编辑"按钮
2. 修改任务配置
3. 保存后，如果任务已启用，会自动更新调度器

### 启用/禁用任务

- **启用**：点击"启用"按钮，任务会立即添加到调度器并开始执行
- **禁用**：点击"禁用"按钮，任务会从调度器中移除，停止执行

### 手动触发任务

点击"触发"按钮可以立即执行一次任务，不等待调度时间。

### 查看执行历史

1. 点击"执行历史"按钮
2. 查看该任务的所有执行记录：
   - 执行状态（等待中、运行中、成功、失败）
   - 开始时间、结束时间
   - 执行时长
   - 重试次数
   - 错误信息（如果有）
   - 执行结果

### 查看统计信息

1. 点击"统计"按钮查看单个任务的统计
2. 点击"全局统计"查看所有任务的统计
3. 统计信息包括：
   - 总执行次数
   - 成功/失败次数
   - 运行中的任务数
   - 成功率
   - 平均执行时长
   - 最近执行时间

### 自动刷新

- 页面默认每5秒自动刷新一次，实时显示任务状态
- 可以点击"停止自动刷新"关闭自动刷新
- 可以点击"刷新"手动刷新

---

## 实时进度查看

### 功能说明

当定时任务执行耗时较长时，系统支持：
1. **实时进度更新**：执行器在执行过程中定期更新进度信息
2. **自动刷新**：Web界面自动检测运行中的任务并刷新显示
3. **进度可视化**：显示进度百分比、当前步骤、执行消息等信息

### 快速开始

#### 1. 创建长时间任务用于测试

在Web界面创建任务，配置如下：

**任务配置（JSON格式）**：
```json
{
  "duration_seconds": 30,
  "success_rate": 1.0,
  "message": "长时间任务执行完成",
  "steps": 30
}
```

**说明**：
- `duration_seconds`: 总执行时长（秒），这里设置为30秒
- `steps`: 执行步骤数，这里设置为30步
- 每步约1秒，共30秒完成

#### 2. 触发任务并查看实时进度

1. 点击"触发"按钮，立即执行任务
2. 立即点击"执行历史"按钮
3. 观察执行结果列的实时更新

**预期效果**：
- 执行结果列会显示：
  - `进度: 3%` → `步骤 1/30`
  - `进度: 6%` → `步骤 2/30`
  - `进度: 10%` → `步骤 3/30`
  - ...（持续更新）
  - `进度: 100%` → `步骤 30/30`
- 系统每2秒自动刷新一次
- 任务完成后，自动停止刷新

### 详细配置示例

#### 示例1：短时间任务（快速测试）

```json
{
  "duration_seconds": 5,
  "success_rate": 1.0,
  "message": "快速任务完成",
  "steps": 5
}
```

- 执行时长：5秒
- 步骤数：5步
- 每步：1秒
- 适合快速测试功能

#### 示例2：中等时长任务（演示进度）

```json
{
  "duration_seconds": 20,
  "success_rate": 1.0,
  "message": "中等任务完成",
  "steps": 20
}
```

- 执行时长：20秒
- 步骤数：20步
- 每步：1秒
- 适合演示进度查看功能

#### 示例3：长时间任务（生产环境）

```json
{
  "duration_seconds": 60,
  "success_rate": 0.95,
  "message": "长时间任务完成",
  "steps": 60
}
```

- 执行时长：60秒
- 步骤数：60步
- 每步：1秒
- 成功概率：95%（5%概率失败，用于测试失败场景）

### Web界面操作步骤

#### 步骤1：创建任务

1. 访问：`http://localhost:8000/admin/scheduler`
2. 点击"创建任务"按钮
3. 填写任务信息：
   - **任务名称**：实时进度测试任务
   - **任务类型**：示例任务
   - **间隔秒数**：120（每2分钟执行一次，或使用Cron表达式）
   - **任务配置**：粘贴上面的JSON配置
   - **启用任务**：勾选
4. 点击"提交"

#### 步骤2：触发任务

1. 在任务列表中找到刚创建的任务
2. 点击"触发"按钮
3. 任务立即开始执行

#### 步骤3：查看实时进度

1. 点击"执行历史"按钮
2. 系统自动检测到运行中的任务，开始每2秒刷新
3. 在执行结果列中观察：
   - 进度百分比实时更新
   - 当前步骤/总步骤数实时更新
   - 执行消息实时更新

#### 步骤4：查看完成结果

任务完成后：
1. 状态变为"成功"（绿色标签）
2. 自动刷新停止
3. 点击执行结果可以查看完整的执行信息

### 进度信息结构

执行记录中的 `result` 字段包含以下进度信息：

```json
{
  "current_step": 15,
  "total_steps": 30,
  "progress_percent": 50,
  "status": "running",
  "message": "正在执行步骤 15/30",
  "steps": [
    {
      "step": 1,
      "status": "completed",
      "message": "步骤 1/30 处理完成"
    },
    {
      "step": 2,
      "status": "completed",
      "message": "步骤 2/30 处理完成"
    },
    ...
  ]
}
```

**字段说明**：
- `current_step`: 当前执行的步骤编号
- `total_steps`: 总步骤数
- `progress_percent`: 进度百分比（0-100）
- `status`: 执行状态（"running"表示运行中）
- `message`: 当前执行消息
- `steps`: 已完成的步骤列表

### API使用示例

#### Python示例：创建并监控任务

```python
import requests
import time
import json

# 配置
BASE_URL = "http://localhost:8000"
TOKEN = "YOUR_ACCESS_TOKEN"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. 创建任务
task_data = {
    "name": "API实时进度测试",
    "task_type": "example_task",
    "interval_seconds": 60,
    "config": {
        "duration_seconds": 30,
        "steps": 30,
        "success_rate": 1.0,
        "message": "API创建的任务执行完成"
    },
    "enabled": True
}

response = requests.post(
    f"{BASE_URL}/api/v1/scheduler/tasks",
    headers=HEADERS,
    json=task_data
)
task = response.json()
task_id = task["id"]
print(f"任务创建成功，ID: {task_id}")

# 2. 触发任务
response = requests.post(
    f"{BASE_URL}/api/v1/scheduler/tasks/{task_id}/trigger",
    headers=HEADERS
)
print("任务已触发")

# 3. 获取执行历史，找到最新的执行记录
time.sleep(1)  # 等待执行记录创建
response = requests.get(
    f"{BASE_URL}/api/v1/scheduler/tasks/{task_id}/executions?limit=1",
    headers=HEADERS
)
executions = response.json()["executions"]
if executions:
    execution_id = executions[0]["id"]
    print(f"执行记录ID: {execution_id}")
    
    # 4. 轮询查询进度
    while True:
        response = requests.get(
            f"{BASE_URL}/api/v1/scheduler/tasks/{task_id}/executions/{execution_id}",
            headers=HEADERS
        )
        execution = response.json()
        
        status = execution["status"]
        result = execution.get("result", {})
        
        if status == "running":
            progress = result.get("progress_percent", 0)
            current_step = result.get("current_step", 0)
            total_steps = result.get("total_steps", 0)
            message = result.get("message", "")
            
            print(f"[运行中] 进度: {progress}% | 步骤: {current_step}/{total_steps} | {message}")
        elif status == "success":
            print(f"[成功] 任务执行完成")
            print(f"执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            break
        elif status == "failed":
            print(f"[失败] 任务执行失败: {execution.get('error_message')}")
            break
        
        time.sleep(2)  # 每2秒查询一次
```

---

## 任务编排

### 功能特性

- **串行执行**：按依赖顺序依次执行任务，适合有先后顺序的数据处理流程
- **并行执行**：同时执行多个无依赖关系的任务，提高执行效率
- **混合执行**：支持复杂的依赖关系，自动确定执行顺序
- **失败处理**：支持"停止"或"继续"两种失败处理策略
- **依赖验证**：自动检测循环依赖和无效依赖
- **实时进度**：支持查看编排任务的实时执行进度
- **树形展示**：在任务列表中，编排任务可以展开查看子任务

### 快速开始

#### 1. 创建基础任务

首先，您需要创建一些基础任务作为编排任务的组成部分。这些任务可以是任何类型的任务（示例任务、数据同步任务等）。

#### 2. 创建编排任务

在Web界面中：

1. 点击"创建任务"按钮
2. 选择任务类型为"编排任务"
3. 填写任务名称和描述
4. 配置执行计划（Cron表达式或间隔秒数）
5. 在"任务配置"中填写编排配置（JSON格式）

#### 3. 编排配置格式

编排任务的配置是一个JSON对象，包含以下字段：

```json
{
  "workflow_type": "serial",  // 或 "parallel"
  "tasks": [
    {
      "task_id": 1,
      "name": "任务1",
      "dependencies": []
    },
    {
      "task_id": 2,
      "name": "任务2",
      "dependencies": [1]  // 依赖任务1
    },
    {
      "task_id": 3,
      "name": "任务3",
      "dependencies": [2]  // 依赖任务2
    }
  ],
  "on_failure": "stop"  // 或 "continue"
}
```

#### 配置字段说明

- **workflow_type**（必需）：
  - `"serial"`：串行执行，按依赖顺序依次执行
  - `"parallel"`：并行执行，同时执行无依赖关系的任务

- **tasks**（必需）：任务列表，每个任务包含：
  - `task_id`：任务ID（必需）
  - `name`：任务名称（必需，用于显示）
  - `dependencies`：依赖的任务ID列表（可选，默认为空数组）

- **on_failure**（可选）：
  - `"stop"`：遇到失败时停止执行（默认）
  - `"continue"`：遇到失败时继续执行其他任务

### 执行模式详解

#### 串行执行（Serial）

串行执行模式会按照依赖关系确定的顺序，依次执行每个任务。只有当一个任务的所有依赖任务都完成后，才会执行该任务。

**示例场景**：
- 数据清洗 → 数据转换 → 数据入库
- 文件下载 → 文件解析 → 数据处理

**配置示例**：
```json
{
  "workflow_type": "serial",
  "tasks": [
    {
      "task_id": 1,
      "name": "步骤1：数据清洗",
      "dependencies": []
    },
    {
      "task_id": 2,
      "name": "步骤2：数据转换",
      "dependencies": [1]
    },
    {
      "task_id": 3,
      "name": "步骤3：数据入库",
      "dependencies": [2]
    }
  ],
  "on_failure": "stop"
}
```

**执行流程**：
```
任务1（数据清洗）
  ↓
任务2（数据转换）
  ↓
任务3（数据入库）
```

#### 并行执行（Parallel）

并行执行模式会同时执行所有无依赖关系的任务。系统会自动根据依赖关系确定哪些任务可以并行执行。

**示例场景**：
- 同时从多个数据源同步数据
- 同时处理多个独立的文件
- 同时执行多个数据校验任务

**配置示例**：
```json
{
  "workflow_type": "parallel",
  "tasks": [
    {
      "task_id": 1,
      "name": "同步数据源A",
      "dependencies": []
    },
    {
      "task_id": 2,
      "name": "同步数据源B",
      "dependencies": []
    },
    {
      "task_id": 3,
      "name": "同步数据源C",
      "dependencies": []
    }
  ],
  "on_failure": "continue"
}
```

**执行流程**：
```
任务1（数据源A） ┐
任务2（数据源B） ├─ 同时执行
任务3（数据源C） ┘
```

#### 混合执行（Parallel with Dependencies）

在并行执行模式下，如果任务之间存在依赖关系，系统会自动处理：

- 无依赖的任务会立即并行执行
- 有依赖的任务会等待其依赖任务完成后才执行
- 多个任务可以同时等待同一个依赖任务

**配置示例**：
```json
{
  "workflow_type": "parallel",
  "tasks": [
    {
      "task_id": 1,
      "name": "任务1",
      "dependencies": []
    },
    {
      "task_id": 2,
      "name": "任务2",
      "dependencies": []
    },
    {
      "task_id": 3,
      "name": "任务3",
      "dependencies": [1, 2]  // 依赖任务1和任务2
    },
    {
      "task_id": 4,
      "name": "任务4",
      "dependencies": [3]  // 依赖任务3
    }
  ],
  "on_failure": "stop"
}
```

**执行流程**：
```
阶段1（并行）：
  任务1 ┐
  任务2 ┘
        ↓
阶段2（串行）：
  任务3
        ↓
阶段3（串行）：
  任务4
```

### 使用示例

#### 示例1：创建串行编排任务

**场景**：需要按顺序执行数据清洗、数据转换、数据入库三个步骤。

**步骤**：

1. 确保已创建以下基础任务：
   - 任务1：数据清洗（ID: 1）
   - 任务2：数据转换（ID: 2）
   - 任务3：数据入库（ID: 3）

2. 创建编排任务，配置如下：
```json
{
  "workflow_type": "serial",
  "tasks": [
    {
      "task_id": 1,
      "name": "数据清洗",
      "dependencies": []
    },
    {
      "task_id": 2,
      "name": "数据转换",
      "dependencies": [1]
    },
    {
      "task_id": 3,
      "name": "数据入库",
      "dependencies": [2]
    }
  ],
  "on_failure": "stop"
}
```

3. 设置执行计划（如：每天凌晨2点执行）

4. 保存并启用任务

#### 示例2：创建并行编排任务

**场景**：需要同时从三个不同的数据源同步数据。

**步骤**：

1. 确保已创建以下基础任务：
   - 任务1：同步数据源A（ID: 1）
   - 任务2：同步数据源B（ID: 2）
   - 任务3：同步数据源C（ID: 3）

2. 创建编排任务，配置如下：
```json
{
  "workflow_type": "parallel",
  "tasks": [
    {
      "task_id": 1,
      "name": "同步数据源A",
      "dependencies": []
    },
    {
      "task_id": 2,
      "name": "同步数据源B",
      "dependencies": []
    },
    {
      "task_id": 3,
      "name": "同步数据源C",
      "dependencies": []
    }
  ],
  "on_failure": "continue"
}
```

3. 设置执行计划（如：每小时执行一次）

4. 保存并启用任务

#### 示例3：使用脚本创建示例

运行以下脚本可以快速创建编排任务示例：

```bash
python scripts/init_scheduler.py --workflow-only
```

或者运行完整初始化：

```bash
python scripts/init_scheduler.py
```

这个脚本会创建：
- 4个基础示例任务
- 1个串行编排任务示例
- 1个并行编排任务示例
- 1个混合编排任务示例

### 树形展示功能

在任务列表中，编排任务支持展开查看子任务：

1. **展开按钮**：只有编排任务（`task_type === 'workflow'`）会显示展开按钮（"+"号）
2. **展开查看**：点击展开按钮，会显示该编排任务包含的所有子任务
3. **子任务操作**：子任务可以正常操作（编辑、触发、启用/禁用等）
4. **视觉区分**：子任务有明显的视觉标识（缩进、图标等）

---

## 任务类型

### 手动任务 (manual_task)

手动任务不支持自动调度，只能通过手动触发执行。适用于：
- 需要按需执行的任务
- 不固定时间执行的任务
- 临时性任务

**特点**：
- 不支持 Cron 表达式调度
- 不支持间隔调度
- 不自动添加到调度器
- 只能通过"触发"按钮手动执行
- 使用通用任务执行器执行

**使用场景**：
- 数据修复任务
- 临时数据分析任务
- 按需执行的报表生成任务

### 通用任务 (common_task)

通用任务支持自动调度，可以独立执行。支持：
- Cron 表达式调度
- 间隔调度
- 命令执行
- 数据同步任务

**数据同步任务类型**：
- `data_sync_stock_list`: 同步股票列表
- `data_sync_trading_calendar`: 同步交易日历
- `data_sync_daily_data`: 同步单只股票的日线数据
- `data_sync_all_daily_data`: 同步所有股票的日线数据

### 编排任务 (workflow)

支持将多个任务组合在一起，按照指定的顺序（串行或并行）执行。详见[任务编排](#任务编排)章节。

### 示例任务 (example_task)

用于演示定时任务功能，支持：
- 可配置的执行时长
- 可配置的成功/失败概率
- 详细的执行步骤记录

---

## Cron表达式

### 格式说明

Cron表达式格式：`分 时 日 月 周`

### 字段说明

- **分**：0-59
- **时**：0-23
- **日**：1-31
- **月**：1-12 或 JAN-DEC
- **周**：0-7（0和7都表示周日）或 SUN-SAT

### 特殊字符

- `*`：匹配所有值
- `,`：列表分隔符，如 `1,3,5`
- `-`：范围，如 `1-5`
- `/`：步长，如 `0/15`（每15分钟）
- `?`：不指定（仅用于日和周字段）

### 常用示例

- `0 18 * * *` - 每天18:00执行
- `0 9 * * 1-5` - 每周一到周五9:00执行
- `0 */2 * * *` - 每2小时执行一次
- `*/30 * * * *` - 每30分钟执行一次
- `0 0 1 * *` - 每月1号0:00执行
- `0 0 * * 1` - 每周一0:00执行

---

## API接口

### 创建任务

```http
POST /api/v1/scheduler/tasks
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "name": "示例任务",
  "task_type": "example_task",
  "interval_seconds": 60,
  "config": {
    "duration_seconds": 3,
    "success_rate": 1.0
  },
  "enabled": true
}
```

### 获取任务列表

```http
GET /api/v1/scheduler/tasks?skip=0&limit=20
Authorization: Bearer YOUR_TOKEN
```

**注意**：默认情况下，子任务（被编排任务引用的任务）不会出现在列表中。

### 获取任务详情

```http
GET /api/v1/scheduler/tasks/{task_id}
Authorization: Bearer YOUR_TOKEN
```

### 更新任务

```http
PUT /api/v1/scheduler/tasks/{task_id}
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "name": "更新后的任务名",
  "config": {...}
}
```

### 删除任务

```http
DELETE /api/v1/scheduler/tasks/{task_id}
Authorization: Bearer YOUR_TOKEN
```

### 启用任务

```http
POST /api/v1/scheduler/tasks/{task_id}/enable
Authorization: Bearer YOUR_TOKEN
```

### 禁用任务

```http
POST /api/v1/scheduler/tasks/{task_id}/disable
Authorization: Bearer YOUR_TOKEN
```

### 触发任务

```http
POST /api/v1/scheduler/tasks/{task_id}/trigger
Authorization: Bearer YOUR_TOKEN
```

### 获取执行历史

```http
GET /api/v1/scheduler/tasks/{task_id}/executions?skip=0&limit=100
Authorization: Bearer YOUR_TOKEN
```

### 获取单个执行记录（实时进度查询）

```http
GET /api/v1/scheduler/tasks/{task_id}/executions/{execution_id}
Authorization: Bearer YOUR_TOKEN
```

返回的执行记录中包含实时进度信息：
```json
{
  "id": 123,
  "task_id": 1,
  "status": "running",
  "start_time": "2025-01-20T10:00:00",
  "result": {
    "current_step": 3,
    "total_steps": 10,
    "progress_percent": 30,
    "message": "正在执行步骤 3/10",
    "steps": [
      {"step": 1, "status": "completed", "message": "步骤 1/10 处理完成"},
      {"step": 2, "status": "completed", "message": "步骤 2/10 处理完成"},
      {"step": 3, "status": "running", "message": "步骤 3/10 处理中"}
    ]
  }
}
```

### 获取统计信息

```http
GET /api/v1/scheduler/stats?task_id={task_id}
Authorization: Bearer YOUR_TOKEN
```

### 编排任务相关接口

#### 获取编排任务中的任务列表

```http
GET /api/v1/scheduler/tasks/{task_id}/workflow
Authorization: Bearer YOUR_TOKEN
```

#### 验证编排任务配置

```http
POST /api/v1/scheduler/tasks/{task_id}/workflow/validate
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "workflow_type": "serial",
  "tasks": [
    {
      "task_id": 1,
      "name": "任务1",
      "dependencies": []
    }
  ],
  "on_failure": "stop"
}
```

---

## 最佳实践

### 1. 任务设计

- **单一职责**：每个基础任务应该只做一件事
- **可复用性**：设计任务时考虑可复用性
- **错误处理**：确保每个任务都有适当的错误处理

### 2. 调度时间

- 避免在高峰期执行大量任务
- 合理设置任务执行间隔，避免资源竞争

### 3. 重试配置

- 根据任务重要性设置合理的重试次数
- 设置合适的重试间隔，避免频繁重试

### 4. 监控告警

- 定期查看任务执行历史和统计信息
- 检查失败任务的错误信息，及时修复

### 5. 编排任务设计

- **依赖关系**：避免循环依赖，尽量减少不必要的依赖
- **失败处理**：
  - `stop`模式：适用于必须按顺序完成的流程
  - `continue`模式：适用于可以容忍部分失败的场景
- **性能优化**：
  - 对于无依赖关系的任务，使用并行执行可以提高效率
  - 合理划分任务粒度，避免任务过大或过小
  - 并行执行时注意系统资源限制

### 6. 实时进度

- **合理设置步骤数**：
  - 步骤数越多，进度更新越频繁，但也会增加数据库写入
  - 建议：执行时长（秒）≈ 步骤数，每步约1秒
- **监控长时间任务**：
  - 对于执行时间超过30秒的任务，建议开启实时进度查看
  - 可以通过执行历史实时了解任务执行情况

---

## 故障排查

### 任务不执行

**症状**：任务配置正确，但从未执行过。

**排查步骤**：
1. **检查任务是否已启用**
   - 在任务列表中查看任务状态
   - 确保 `enabled` 字段为 `true`
   - 如果被禁用，点击"启用"按钮

2. **检查调度配置**
   - Cron表达式格式是否正确（使用在线工具验证）
   - 间隔调度的时间间隔是否合理（不能为0或负数）
   - 检查时区设置是否正确

3. **检查调度器状态**
   - 查看后端服务日志：`logs/zquant.log`
   - 确认调度器已启动（日志中应该有 "Scheduler started" 信息）
   - 检查是否有调度器相关的错误信息

4. **验证任务配置**
   - 检查任务类型是否正确
   - 确认任务函数路径和参数正确
   - 尝试手动触发任务，看是否能执行

**常见错误**：
- `任务未启用`：在任务列表中启用任务
- `Cron表达式无效`：使用Cron表达式验证工具检查格式
- `调度器未启动`：重启后端服务

### 任务执行失败

**症状**：任务被调度执行，但执行失败。

**排查步骤**：
1. **查看执行历史**
   - 在任务执行历史中查看错误信息
   - 查看完整的错误堆栈信息
   - 注意错误发生的时间点

2. **检查任务配置**
   - 验证任务函数路径是否正确
   - 检查任务参数是否正确
   - 确认任务函数是否存在且可访问

3. **检查依赖服务**
   - 数据库连接是否正常
   - Redis服务是否运行
   - 外部API服务是否可访问
   - 文件系统权限是否正确

4. **查看详细日志**
   - 查看日志文件：`logs/zquant.log`
   - 搜索任务名称或任务ID
   - 查看错误发生前后的日志信息

**常见错误**：
- `数据库连接失败`：检查数据库配置和连接状态
- `模块导入错误`：检查Python路径和模块是否存在
- `参数错误`：检查任务参数格式和类型
- `权限不足`：检查文件系统权限

### 任务状态不更新

**症状**：任务执行后，前端显示的状态没有更新。

**排查步骤**：
1. **检查自动刷新**
   - 确认前端自动刷新功能已开启
   - 检查浏览器控制台是否有错误
   - 尝试手动点击"刷新"按钮

2. **检查网络连接**
   - 确认API服务正常运行
   - 检查网络连接是否稳定
   - 查看浏览器开发者工具的网络请求

3. **检查后端服务**
   - 确认后端服务正常运行
   - 查看API响应是否正常
   - 检查数据库中的任务状态是否正确

**解决方案**：
- 刷新浏览器页面
- 检查浏览器缓存
- 重启前端服务

### 看不到实时进度

**症状**：任务正在执行，但看不到进度更新。

**可能原因**：
1. **任务执行太快**
   - 任务在几秒内完成，进度更新来不及显示
   - 任务没有正确更新进度信息

2. **进度更新未实现**
   - 任务执行器没有调用 `update_progress` 方法
   - 步骤数设置不合理

**解决方案**：
1. **增加步骤数**
   - 在任务配置中增加 `steps` 参数
   - 建议：执行时长（秒）≈ 步骤数，每步约1秒
   - 例如：预计执行60秒的任务，设置 `steps=60`

2. **检查进度更新代码**
   - 确保任务执行器正确调用了 `update_progress`
   - 检查进度更新的频率是否合理
   - 验证进度值是否在0-100之间

3. **监控长时间任务**
   - 对于执行时间超过30秒的任务，建议开启实时进度查看
   - 可以通过执行历史实时了解任务执行情况

### 自动刷新不工作

**症状**：前端自动刷新功能不工作，需要手动刷新才能看到最新状态。

**可能原因**：
1. **没有运行中的任务**
   - 自动刷新只在有运行中任务时才工作
   - 所有任务都已完成或失败

2. **浏览器标签页被隐藏**
   - 某些浏览器在标签页隐藏时会暂停定时器
   - 切换到其他标签页或最小化窗口

3. **前端服务问题**
   - 前端服务异常
   - JavaScript错误导致定时器停止

**解决方案**：
1. **确认任务状态**
   - 检查是否有状态为 "running" 的任务
   - 如果没有，自动刷新不会工作（这是正常行为）

2. **保持标签页激活**
   - 保持浏览器标签页处于激活状态
   - 避免切换到其他标签页

3. **手动刷新**
   - 点击"刷新"按钮手动更新
   - 刷新浏览器页面

4. **检查前端服务**
   - 查看浏览器控制台是否有错误
   - 重启前端服务

### 编排任务相关问题

#### 问题1：配置验证失败

**错误信息**：`编排任务配置无效: 以下任务不存在: {1, 2}`

**解决方案**：
- 检查任务ID是否正确
- 确保所有引用的任务都已创建

#### 问题2：检测到循环依赖

**错误信息**：`检测到循环依赖，任务 X 存在循环依赖关系`

**解决方案**：
- 检查任务的依赖关系
- 移除循环依赖

#### 问题3：任务未启用

**错误信息**：`以下任务未启用: [1, 2]`

**解决方案**：
- 在任务列表中启用相关任务
- 或者从编排任务中移除未启用的任务

#### 问题4：执行失败

**可能原因**：
- 子任务执行失败
- 依赖关系配置错误
- 系统资源不足（并行执行时）

**解决方案**：
- 查看执行历史，找到失败的具体任务
- 检查子任务的配置和状态
- 调整并行执行的任务数量

---

## 总结

定时任务系统提供了完整的任务管理功能，支持：
- ✅ 灵活的调度配置（Cron和间隔）
- ✅ 实时状态监控
- ✅ 完整的执行历史记录
- ✅ 实时进度查看
- ✅ 任务编排（串行/并行）
- ✅ 树形展示子任务
- ✅ Web界面管理
- ✅ API接口调用

通过初始化脚本可以快速创建示例任务和编排任务，快速了解和使用定时任务功能。


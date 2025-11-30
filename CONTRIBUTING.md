# 贡献指南

感谢您对 ZQuant 项目的关注！我们欢迎所有形式的贡献。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交代码](#提交代码)
- [Pull Request 流程](#pull-request-流程)

## 行为准则

本项目遵循 [贡献者行为准则](CODE_OF_CONDUCT.md)。参与项目时，请保持尊重和包容的态度。

## 如何贡献

### 报告 Bug

如果您发现了 Bug，请通过以下方式报告：

1. **检查现有 Issues**: 在 [Issues](https://github.com/zquant/zquant/issues) 中搜索，确认该问题尚未被报告
2. **创建新 Issue**: 如果问题不存在，请创建新 Issue，包含以下信息：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为和实际行为
   - 环境信息（Python版本、操作系统等）
   - 错误日志（如果有）

### 提出功能请求

我们欢迎新功能的建议！请：

1. 在 [Issues](https://github.com/zquant/zquant/issues) 中搜索类似的功能请求
2. 如果不存在，创建新 Issue，说明：
   - 功能描述和使用场景
   - 为什么这个功能对项目有价值
   - 可能的实现方案（可选）

### 改进文档

文档改进同样重要！您可以：

- 修正拼写错误
- 改进文档结构
- 添加使用示例
- 翻译文档

### 提交代码

代码贡献是最直接的贡献方式。请遵循以下流程：

## 开发环境设置

### 1. Fork 和克隆仓库

```bash
# Fork 仓库到您的 GitHub 账户
# 然后克隆您的 Fork
git clone https://github.com/YOUR_USERNAME/zquant.git
cd zquant

# 添加上游仓库
git remote add upstream https://github.com/zquant/zquant.git
```

### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，配置数据库、Redis等
```

### 5. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE zquant CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 运行迁移
alembic upgrade head
```

### 6. 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=zquant --cov-report=html
```

## 代码规范

### Python 代码风格

项目使用以下工具进行代码格式化和检查：

- **Ruff**: 代码检查和格式化（推荐）
- **Black**: 代码格式化
- **isort**: 导入排序

#### 代码检查

```bash
# 使用 Ruff 检查代码
ruff check zquant/

# 自动修复可修复的问题
ruff check --fix zquant/
```

#### 代码格式化

```bash
# 使用 Ruff 格式化（推荐）
ruff format zquant/

# 或使用 Black
black zquant/
isort zquant/
```

#### 提交前检查

项目支持 pre-commit hooks，可以在提交前自动检查代码：

```bash
# 安装 pre-commit
pip install pre-commit

# 安装 Git hooks
pre-commit install

# 手动运行所有检查
pre-commit run --all-files
```

### 代码规范要求

1. **遵循 PEP 8**: Python 代码风格指南
2. **类型提示**: 尽量使用类型提示
3. **文档字符串**: 为函数和类添加文档字符串
4. **测试覆盖**: 新功能应包含测试用例
5. **行长度**: 最大 120 字符

### 提交信息规范

提交信息应清晰描述更改内容：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 类型**:
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

**示例**:
```
feat(backtest): 添加策略管理功能

- 实现策略增删改查API
- 添加策略模板库
- 支持从策略库选择策略进行回测

Closes #123
```

## 提交代码

### 1. 创建功能分支

```bash
# 从 main 分支创建新分支
git checkout main
git pull upstream main
git checkout -b feature/your-feature-name

# 或修复 Bug
git checkout -b fix/your-bug-name
```

### 2. 进行更改

- 编写代码
- 添加测试
- 更新文档
- 确保代码通过所有检查

### 3. 提交更改

```bash
# 添加更改的文件
git add .

# 提交（使用清晰的提交信息）
git commit -m "feat(backtest): 添加策略管理功能"

# 如果提交信息较长，可以使用多行
git commit
```

### 4. 保持分支同步

```bash
# 定期从上游拉取最新更改
git fetch upstream
git rebase upstream/main
```

### 5. 推送更改

```bash
# 推送到您的 Fork
git push origin feature/your-feature-name
```

## Pull Request 流程

### 1. 创建 Pull Request

1. 在 GitHub 上打开您的 Fork
2. 点击 "New Pull Request"
3. 选择您的分支和目标分支（通常是 `main`）
4. 填写 PR 描述，包括：
   - 更改的目的和背景
   - 实现方式
   - 测试情况
   - 相关 Issue（如果有）

### 2. PR 检查清单

在提交 PR 前，请确认：

- [ ] 代码遵循项目代码规范
- [ ] 所有测试通过
- [ ] 添加了必要的测试用例
- [ ] 更新了相关文档
- [ ] 提交信息清晰明确
- [ ] 没有合并冲突
- [ ] 代码已通过 lint 检查

### 3. 代码审查

- 维护者会审查您的 PR
- 可能会要求修改或提供更多信息
- 请及时响应审查意见

### 4. 合并

- 审查通过后，维护者会合并您的 PR
- 合并后，您的贡献将出现在项目历史中

## 开发提示

### 运行开发服务器

```bash
# 启动开发服务器（支持热重载）
uvicorn zquant.main:app --reload --host 0.0.0.0 --port 8000
```

### 查看 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## 获取帮助

如果您在贡献过程中遇到问题：

- 查看 [文档](https://docs.zquant.com)
- 在 [Issues](https://github.com/zquant/zquant/issues) 中搜索相关问题
- 创建新 Issue 询问
- 联系维护者: kevin@vip.qq.com

## 致谢

感谢所有为 ZQuant 项目做出贡献的开发者！您的贡献使这个项目变得更好。

---

**再次感谢您的贡献！** 🎉



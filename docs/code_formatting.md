# 代码格式化和检查工具使用指南

本项目使用 `ruff`、`black` 和 `isort` 进行代码格式化和检查。

## 工具介绍

### Ruff
- **功能**: 极快的 Python linter 和代码格式化工具
- **优势**: 
  - 速度极快（Rust 编写）
  - 可以替代 flake8、isort、black 等多个工具
  - 内置格式化功能（兼容 Black 风格）
- **文档**: https://docs.astral.sh/ruff/

### Black
- **功能**: 代码格式化工具
- **特点**: 不可配置的代码风格（"不妥协"的格式化工具）
- **文档**: https://black.readthedocs.io/

### isort
- **功能**: 导入排序工具
- **特点**: 自动整理 Python 导入语句
- **文档**: https://pycqa.github.io/isort/

## 安装

```bash
# 方式一：单独安装
pip install ruff black isort

# 方式二：从 requirements.txt 安装
pip install -r requirements.txt

# 方式三：安装 pre-commit（可选，用于 Git hooks）
pip install pre-commit
pre-commit install
```

## 快速开始

### 使用 Ruff（推荐）

Ruff 是最快的选择，可以同时进行代码检查和格式化：

```bash
# 检查代码（不修改文件）
ruff check zquant/

# 自动修复可修复的问题
ruff check --fix zquant/

# 格式化代码（兼容 Black 风格）
ruff format zquant/

# 同时检查和格式化
ruff check --fix zquant/ && ruff format zquant/
```

### 使用便捷脚本

项目提供了便捷脚本，支持 Windows 和 Linux/Mac：

**Linux/Mac:**
```bash
bash .format.sh check   # 检查代码
bash .format.sh fix     # 自动修复并格式化
bash .format.sh format  # 仅格式化（默认）
bash .format.sh all     # 完整流程
```

**Windows:**
```cmd
.format.bat check   # 检查代码
.format.bat fix     # 自动修复并格式化
.format.bat format  # 仅格式化（默认）
.format.bat all     # 完整流程
```

### 使用 Black + isort（传统方式）

```bash
# 格式化代码
black zquant/

# 排序导入
isort zquant/

# 同时执行
black zquant/ && isort zquant/
```

## 配置说明

所有工具的配置都在 `pyproject.toml` 文件中：

### Ruff 配置

```toml
[tool.ruff]
line-length = 120
target-version = "py311"
select = ["E", "W", "F", "I", "N", "UP", "B", ...]
```

### Black 配置

```toml
[tool.black]
line-length = 120
target-version = ["py311"]
```

### isort 配置

```toml
[tool.isort]
profile = "black"
line_length = 120
known_first_party = ["zquant"]
```

## 常用命令

### Ruff 命令

```bash
# 检查整个项目
ruff check .

# 格式化整个项目
ruff format .

# 只检查特定文件
ruff check zquant/api/v1/config.py

# 只格式化特定文件
ruff format zquant/api/v1/config.py

# 查看所有可修复的问题
ruff check --output-format=concise .

# 自动修复所有可修复的问题
ruff check --fix .

# 只检查导入顺序
ruff check --select I zquant/

# 显示帮助
ruff check --help
ruff format --help
```

### Black 命令

```bash
# 格式化代码
black zquant/

# 检查代码（不修改）
black --check zquant/

# 显示差异
black --diff zquant/

# 格式化特定文件
black zquant/api/v1/config.py
```

### isort 命令

```bash
# 排序导入
isort zquant/

# 检查导入顺序（不修改）
isort --check-only zquant/

# 显示差异
isort --diff zquant/

# 排序特定文件
isort zquant/api/v1/config.py
```

## IDE 集成

### VS Code

1. 安装扩展：
   - **Ruff** (astral-sh.ruff)
   - **Black Formatter** (ms-python.black-formatter)

2. 配置 `settings.json`:
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "ruff.enable": true,
  "ruff.format.args": ["--line-length=120"],
  "black-formatter.args": ["--line-length=120"]
}
```

### PyCharm

1. 打开 Settings -> Tools -> External Tools
2. 添加 Ruff：
   - Name: Ruff Check
   - Program: `$PyInterpreterDirectory$/ruff`
   - Arguments: `check $FilePath$`
   - Working directory: `$ProjectFileDir$`
3. 添加 Black：
   - Name: Black Format
   - Program: `$PyInterpreterDirectory$/black`
   - Arguments: `$FilePath$`
   - Working directory: `$ProjectFileDir$`
4. 配置快捷键（Settings -> Keymap）

### Cursor / VS Code (基于 VS Code)

配置与 VS Code 相同，安装相同的扩展即可。

## 工作流程建议

### 开发时

1. 编写代码
2. 保存时自动格式化（如果配置了 formatOnSave）
3. 提交前运行检查

### 提交前

**方式一：使用 pre-commit（推荐）**

如果安装了 pre-commit，Git 提交时会自动运行检查：

```bash
# 安装 pre-commit hooks
pre-commit install

# 之后每次 git commit 时会自动运行检查
git commit -m "your message"

# 手动运行所有 hooks
pre-commit run --all-files
```

**方式二：使用脚本**

```bash
# Linux/Mac
bash .format.sh fix

# Windows
.format.bat fix
```

**方式三：手动执行**

```bash
ruff check --fix zquant/ && ruff format zquant/
```

### CI/CD 集成

在 CI 流程中添加：

```yaml
# GitHub Actions 示例
- name: Check code formatting
  run: |
    ruff check .
    ruff format --check .
```

## 工具选择建议

### 推荐方案：只使用 Ruff

Ruff 可以完全替代 isort 和 black，速度最快：

```bash
# 检查和格式化
ruff check --fix . && ruff format .
```

### 兼容方案：Ruff + Black

如果团队已经熟悉 Black，可以继续使用：

```bash
# 使用 Ruff 检查
ruff check --fix .

# 使用 Black 格式化（Ruff format 兼容 Black，但 Black 更成熟）
black .
```

### 传统方案：Black + isort

如果不想使用 Ruff：

```bash
black . && isort .
```

## 配置说明

### 行长度

所有工具统一设置为 **120 字符**，在 `pyproject.toml` 中配置。

### 排除文件

以下文件/目录被排除：
- `__pycache__/`
- `.venv/`, `venv/`
- `node_modules/`
- `alembic/versions/`
- `dist/`, `build/`

### 导入排序规则

1. 标准库导入
2. 第三方库导入
3. 第一方包（zquant）导入
4. 本地文件导入

## 常见问题

### Q: Ruff 和 Black 冲突吗？

A: 不会。Ruff 的格式化功能兼容 Black 风格，可以安全地一起使用。但建议只使用一个格式化工具。

### Q: 应该使用哪个工具？

A: 
- **推荐**: 只使用 Ruff（最快，功能最全）
- **兼容**: Ruff + Black（如果团队已熟悉 Black）
- **传统**: Black + isort（如果不想使用 Ruff）

### Q: 如何只检查不修改？

A: 使用 `--check` 参数：
```bash
ruff check .          # 只检查
black --check .       # 只检查
isort --check-only .  # 只检查
```

### Q: 如何忽略某些规则？

A: 在 `pyproject.toml` 的 `[tool.ruff]` 部分添加 `ignore` 列表。

## 更多资源

- [Ruff 文档](https://docs.astral.sh/ruff/)
- [Black 文档](https://black.readthedocs.io/)
- [isort 文档](https://pycqa.github.io/isort/)


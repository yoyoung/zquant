# Pre-commit 网络问题解决方案

如果在使用 pre-commit 时遇到网络连接问题（无法访问 GitHub），可以使用以下解决方案。

## 问题现象

```
fatal: unable to access 'https://github.com/...': Failed to connect to github.com port 443
```

## 解决方案

### 方案一：使用本地工具（已配置，推荐）

项目已配置为使用本地安装的 ruff，无需从 GitHub 下载：

```yaml
- repo: local
  hooks:
    - id: ruff
      entry: ruff check --fix
      language: system
```

**优点**：
- 无需网络连接
- 使用本地已安装的工具
- 速度更快

**缺点**：
- 无法使用 pre-commit-hooks（需要从 GitHub 下载）

### 方案二：配置代理

如果已配置代理，可以设置环境变量：

**Windows (PowerShell):**
```powershell
$env:HTTP_PROXY="http://proxy.example.com:8080"
$env:HTTPS_PROXY="http://proxy.example.com:8080"
pre-commit install
```

**Linux/Mac:**
```bash
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"
pre-commit install
```

### 方案三：使用镜像源

可以配置 Git 使用镜像源：

```bash
# 配置 Git 使用镜像
git config --global url."https://mirror.ghproxy.com/https://github.com/".insteadOf "https://github.com/"

# 或者使用其他镜像
git config --global url."https://github.com.cnpmjs.org/".insteadOf "https://github.com/"
```

### 方案四：手动下载并安装

1. 手动下载 pre-commit hooks 仓库
2. 放到本地目录
3. 修改 `.pre-commit-config.yaml` 使用本地路径

### 方案五：暂时禁用 pre-commit

如果不需要自动检查，可以暂时卸载：

```bash
pre-commit uninstall
```

然后手动运行检查：

```bash
# 使用脚本
bash .format.sh fix

# 或手动运行
ruff check --fix . && ruff format .
```

## 当前配置说明

项目当前配置：
- ✅ 使用本地 ruff（无需网络）
- ❌ pre-commit-hooks 已注释（需要网络）

如果需要使用 pre-commit-hooks，请：
1. 配置代理或镜像
2. 取消 `.pre-commit-config.yaml` 中 pre-commit-hooks 的注释
3. 运行 `pre-commit install`

## 验证配置

测试 ruff hook 是否正常工作：

```bash
# 测试 ruff 检查
pre-commit run ruff --all-files

# 测试 ruff 格式化
pre-commit run ruff-format --all-files

# 运行所有 hooks
pre-commit run --all-files
```

## 相关文档

- [Pre-commit 官方文档](https://pre-commit.com/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [代码格式化指南](./code_formatting.md)


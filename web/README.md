# ZQuant量化分析平台

This project is initialized with [Ant Design Pro](https://pro.ant.design). Follow is the quick guide for how to use.

## Environment Prepare

Install `node_modules`:

```bash
npm install
```

or

```bash
yarn
```

## API配置

前端API地址可以通过环境变量配置：

### 方式1：设置完整的API基础URL（推荐）

在项目根目录创建 `.env` 文件（或 `.env.local`）：

```bash
REACT_APP_API_BASE_URL=http://192.168.1.100:8000
```

### 方式2：分别设置主机和端口

```bash
REACT_APP_API_HOST=192.168.1.100
REACT_APP_API_PORT=8000
```

### 默认值

- 开发环境：使用代理，无需配置（代理到 `http://localhost:8000`）
- 生产环境：默认使用 `http://localhost:8000`

### 配置说明

- `REACT_APP_API_BASE_URL`: 完整的API基础URL（优先级最高）
- `REACT_APP_API_HOST`: API服务器主机地址（默认：localhost）
- `REACT_APP_API_PORT`: API服务器端口（默认：8000）

配置文件位置：`web/config/api.ts`

## Provided Scripts

ZQuant量化分析平台 provides some useful script to help you quick start and build with web project, code style check and test.

Scripts provided in `package.json`. It's safe to modify or add additional script:

### Start project

```bash
npm start
```

### Build project

```bash
npm run build
```

### Check code style

```bash
npm run lint
```

You can also use script to auto fix some lint error:

```bash
npm run lint:fix
```

### Test code

```bash
npm test
```

## More

You can view full document on our [official website](https://pro.ant.design). And welcome any feedback in our [github](https://github.com/zquant/zquant).

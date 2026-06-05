# Skill: docker-deploy

## 描述

使用 Docker Compose 构建和部署全栈应用。包括镜像构建、服务启动、日志查看和故障排查。

## 触发条件

- 用户说"部署"、"Docker 启动"、"docker-compose up"
- 需要生产环境部署
- 验证 Docker 配置是否正确

## 执行步骤

### 步骤 1: 验证 Docker 环境

```bash
docker --version
docker compose version
```

要求 Docker ≥24.0, docker-compose ≥2.0。

### 步骤 2: 构建镜像

```bash
cd /home/wg/文档/Learning/Project/YanGuan-NLP

# 构建（不缓存，确保最新）
docker compose build --no-cache
```

### 步骤 3: 启动服务

```bash
# 后台启动
docker compose up -d

# 查看启动状态
docker compose ps
```

预期输出：
```
NAME                    STATUS              PORTS
yanguan-backend      Up 30 seconds       0.0.0.0:3001->3001/tcp
yanguan-frontend     Up 5 seconds        0.0.0.0:3000->80/tcp
```

### 步骤 4: 验证服务

```bash
# 后端健康检查
curl http://localhost:3001/api/health
# 预期: {"status":"healthy","version":"0.1.0"}

# 后端仪表盘
curl http://localhost:3001/api/dashboard
# 预期: {"code":200,"data":{...}}

# 前端页面
curl http://localhost:3000/
# 预期: HTML 页面
```

### 步骤 5: 导入数据（如数据库为空）

```bash
# 进入后端容器执行 seed
docker compose exec backend python scripts/seed_db.py
```

### 步骤 6: 查看日志

```bash
# 所有服务
docker compose logs -f

# 仅后端
docker compose logs -f backend

# 仅前端
docker compose logs -f frontend

# 最近 50 行
docker compose logs --tail=50 backend
```

### 步骤 7: 进入容器调试

```bash
# 进入后端容器
docker compose exec backend bash

# 进入前端容器
docker compose exec frontend sh
```

## 停止和清理

```bash
# 停止服务（保留数据卷）
docker compose down

# 停止服务 + 删除数据卷（完全重置）
docker compose down -v

# 停止 + 删除镜像
docker compose down --rmi all -v
```

## 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `backend is unhealthy` | 后端启动慢或失败 | 查看日志 `docker compose logs backend` |
| `port already in use` | 3001/3000 端口被占用 | `lsof -i :3001` 找到进程并停止 |
| `yanguan.db permission denied` | 数据卷权限问题 | `chmod -R 777 backend/data/db` |
| `ModuleNotFoundError` | 镜像构建时依赖安装失败 | `docker compose build --no-cache backend` |
| 前端无法访问后端 | nginx proxy 配置问题 | 检查 `frontend/nginx.conf` 的 proxy_pass |
| 数据库为空 | 未运行 seed | `docker compose exec backend python scripts/seed_db.py` |

## 生产环境调整

当前配置适用于开发/演示环境。生产部署建议：
1. 使用 PostgreSQL 替代 SQLite
2. 前端使用 CDN 托管静态文件
3. 后端使用 `gunicorn + uvicorn workers`
4. 添加 HTTPS 反向代理（nginx + Let's Encrypt）
5. 配置持久化日志收集

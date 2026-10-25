# 无足鸟古诗词学习助手（bai）

> 古诗词学习与长文深度阅读的跨端应用。**免费 · 易用 · 安全 · 开源**。
>
> 用户认证由独立 auth 服务统一承载，书籍云同步密钥仅存服务端，亦可自行部署。开源地址：<https://github.com/wuzuniao/bai>

[![License](https://img.shields.io/badge/license-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688.svg)](https://fastapi.tiangolo.com/)
[![uni-app x](https://img.shields.io/badge/uni--app%20x-latest-2B9938.svg)](https://doc.dcloud.net.cn/uni-app-x/)
[![MariaDB](https://img.shields.io/badge/MariaDB-12.3_(LTS)-003545.svg)](https://mariadb.org/)

---

## 功能特性

- **首页诗**：原创长诗《无题》逐字拼音注音呈现，支持划词选区，并作为虚拟书进入阅读器做笔记。
- **书架与导入**：txt 导入（自动编码识别、按章节解析），PDF 原文件导入与渲染（仅 App 端）；未登录可离线导入，登录后自动注册云端并迁移。
- **深度阅读器**：字体/版式设置、目录抽屉、书签、划线、想法批注、分享长图导出相册；阅读进度与笔记云端跟随。
- **阅读统计与排行**：阅读时长按周/月/年统计（总时长/阅读天数/日均），全体用户时长排行榜；时长上报带防刷（按日封顶 + 节奏校验）。
- **活动激励**：每日签到（自然周档位）、阅读时长五档奖励、铜满进银/银满进金自动进位，金币余额与兑换流水全程可查。
- **会员与云同步**：金币购买会员（服务端计价、幂等授权、失败补偿退款）；会员可开启书籍文件云同步（腾讯云 COS，临时凭证按用户目录隔离）。
- **账号体系**：微信一键登录、邮箱注册/登录（auth.wuzuniao.com 统一认证，无足鸟系列产品多端通用）；Web 端跨子域 SSO 免重复登录。

---

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 前端 | uni-app x（UTS，Vue 语法） | 微信小程序 / H5 / App 跨端 |
| 前端 | Pinia / SCSS + 设计令牌 | 状态管理 / 样式（`DESIGN_bai.md` 为唯一真源） |
| 后端 | FastAPI（异步） | RESTful API |
| 后端 | SQLAlchemy / Pydantic | ORM（asyncmy 驱动）/ 数据校验 |
| 后端 | PyJWT / cryptography | RS256 令牌本地验签（JWKS 公钥 + 撤销增量同步） |
| 对象存储 | 腾讯云 COS | 书籍文件云同步（永久密钥仅存后端，STS 临时凭证 + 预签名 URL 直传） |
| 认证服务 | auth（独立项目，auth.wuzuniao.com） | 用户账户体系：注册/登录/令牌签发，本服务持 JWKS 公钥本地验签 |
| 数据库 | MariaDB 12.3 (LTS) | 业务库 `wuzuniao_bai`（用户数据由 auth 认证服务持有） |
| 部署 | Docker | 共享基础设施（MariaDB/Nginx 容器多项目复用）+ 项目专属 FastAPI 容器 |

---

## 项目结构

```
bai/
├── backend/                # 后端（FastAPI）
│   ├── app/
│   │   ├── api/v1/         # 路由（books / reading / preferences / activity / membership / cos / users）
│   │   ├── core/           # 配置 / 数据库 / auth 对接（JWKS 验签+撤销同步）/ 安全 / 依赖注入
│   │   ├── models/         # SQLAlchemy 数据模型
│   │   ├── schemas/        # Pydantic 请求/响应 Schema
│   │   ├── services/       # 业务逻辑（阅读 / 奖励 / 会员 / COS）
│   │   ├── utils/          # 日志等通用工具
│   │   └── main.py         # 应用入口（含令牌撤销同步后台任务）
│   ├── sql/                # 数据库初始化 SQL + 增量变更脚本
│   └── .env.example        # 环境变量模板
├── frontend/               # 前端（uni-app x，HBuilderX 标准布局，无 src 层）
│   ├── api/                # 接口封装（reading / activity / cos / announcement）
│   ├── components/         # 可复用组件（按业务域分组：reader / selection / form / list / common）
│   ├── pages/              # 主包（index / reading）+ 用户分包（user）
│   ├── stores/             # Pinia 状态管理
│   ├── utils/              # 通用工具（请求 / 书籍解析 / 设计令牌 / 阅读数据层 等）
│   └── scripts/            # CLI 构建入口（run-uni.js，与 HBuilderX 共用产物布局）
├── scripts/                # 运维脚本（部署 / 数据库备份）
└── DESIGN_bai.md           # 设计令牌（颜色 / 字体 / 圆角 / 间距）
```

---

## 配置

**后端**：复制 `backend/.env.example` 为 `backend/.env`，字段与 `app/core/config.py` 一一对应，涵盖数据库、auth 对接（`AUTH_*`）、微信小程序凭证、腾讯云 COS（`COS_*`）、接口文档开关与 CORS。

**前端**：配置集中在 `frontend/utils/config.uts` 常量模块（HBuilderX 不加载 `.env`，以常量模块保证多端构建一致）：`AUTH_BASE_URL`、`API_BASE_URL`、`AUTH_CLIENT_ID`、`WX_APPID`。该文件提交 Git，严禁写入密码/密钥。

**数据库**：本服务仅连接业务库 `wuzuniao_bai`（书籍/阅读/活动/会员）；用户账户与认证数据由 auth 认证服务持有，本服务需要用户信息时经 auth 的 `/internal/*` 服务接口查询。初始化 SQL 位于 `backend/sql/create_bai_db.sql`，增量变更追加 `backend/sql/add_*.sql`（脚本幂等可重放，须同步回填建库脚本）。

---

## API

所有接口前缀 `/api/v1`，统一响应格式：

```json
{ "code": 0, "msg": "success", "data": { } }
```

主要模块：书籍（`/books`）、阅读（`/reading`，含时长上报与排行）、偏好（`/preferences`）、活动（`/activity`，签到/奖励/金币）、会员（`/membership`）、对象存储（`/cos`，会员守卫）。受保护接口一律 `Authorization: Bearer <access_token>`，令牌由 auth 认证服务（`https://auth.wuzuniao.com`）签发，本项目后端经 JWKS 公钥本地验签（RS256）、不自行签发令牌。用户认证接口（注册/登录/资料）由 auth 认证服务提供，前端直连。完整接口见 Swagger UI：`http://localhost:11001/docs`（`DOCS_ENABLED` 控制，生产关闭）。

---

## 本地开发

前置：本地先启动 auth 认证服务（端口 11000，独立项目见其仓库 README）——本项目后端启动不依赖 auth 就绪（JWKS 拉取失败自动回退磁盘缓存），但登录联调需要。

```bash
# 后端（默认 11001，可传端口参数覆盖，如 python run.py 11011）
cd backend
pip install -r requirements.txt
python run.py

# 前端（Windows 下须 --force 安装：devDependencies 含 Linux 平台二进制，裸装直接中止）
cd frontend
npm install --force
node scripts/run-uni.js dev h5             # H5 开发
node scripts/run-uni.js build h5           # H5 生产构建
node scripts/run-uni.js build mp-weixin    # 微信小程序（产物 unpackage/dist/build/mp-weixin，导入微信开发者工具上传）
```

---

## 部署

生产架构为「**共享基础设施 + 项目专属后端**」，部署配置集中在 `/opt/deploy`（git 仓库仅存源码）：

- **共享基础设施**（无项目前缀，多项目复用）：`mariadb` 与 `nginx` 容器（nginx 统一承载各项目站点与 H5 静态资源）、`wuzuniao.com` 泛域名证书（acme.sh 自动续期，覆盖全部子域）、数据库数据与统一备份
- **本项目**（`/opt/deploy/bai`）：`bai-backend` 专属容器，经 external 网络访问共享 MariaDB；对外经 nginx `https://bai.wuzuniao.com`（443）反代

部署只需一条命令（脚本幂等：生成 compose 与 nginx 站点配置、初始化业务库与专用用户 `bai_backend`、生成 `.env`、构建 H5——产物已存在则跳过）：

```bash
git clone git@github.com:wuzuniao/bai.git && cd bai
bash scripts/deploy.sh
```

> **部署顺序**：先部署 auth 认证服务（独立项目，见其仓库 README），再部署本项目；本项目 `.env` 的 `AUTH_*` 须与 auth 侧配置一致。

常用运维：

```bash
cd /opt/deploy/bai && docker compose ps    # 本项目后端
cd /opt/deploy && docker compose ps        # 共享基础设施（mariadb / nginx）
```

数据库备份由 `scripts/backup_db.sh` 承担（生产 crontab 每周一 01:00 执行，备份至 `/opt/deploy/data/backup_sql`，仅保留最近 12 份）。

---

## 常见问题（FAQ）

### 这是什么应用？
无足鸟古诗词学习助手是一款免费、开源的阅读应用：首页以注音长诗呈现古诗词学习场景，书架支持导入 txt/PDF 长文深度阅读（划线、想法、书签、分享），并以时长统计、排行榜与签到/奖励激励坚持阅读。

### 支持哪些平台？
微信小程序（主要）、H5 网页、Android/iOS App。同一套 uni-app x 代码跨端运行；PDF 导入与渲染仅 App 端支持（Android 已实现，iOS 待补）。

### 数据安全吗？
传输全程 HTTPS；登录令牌由独立认证服务签发，本项目仅持公钥本地验签、不碰用户密码；COS 永久密钥仅存后端 `.env`，前端只持短时临时凭证与预签名 URL。支持自行部署，数据完全掌握在自己手中。

### 我的书存在哪里？
书籍正文只存设备本地（App 沙盒 / Web 端 IndexedDB），云端仅存元数据；会员可开启云同步，将书籍文件存入对象存储（按用户目录隔离）。

### 开源协议？
GNU GPLv3，开源地址 https://github.com/wuzuniao/bai 。

---

## 项目文档

| 文档 | 说明 |
|------|------|
| [AGENTS.md](AGENTS.md) | AI 编程执行规范（先思考后编码 / 极简主义 / 手术式修改） |
| [项目规范.md](项目规范.md) | 固定项目技术规范（技术栈 / 编码规范 / API 设计 / 环境配置 / Git） |
| [DESIGN_bai.md](DESIGN_bai.md) | 设计令牌唯一真源（颜色 / 字体 / 圆角 / 间距） |

---

## 许可证

本项目基于 [GNU General Public License v3](LICENSE) 开源。

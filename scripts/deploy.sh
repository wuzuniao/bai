#!/bin/bash
# ============================================================
# Bai 后端一键部署脚本
# 适用环境：Rocky Linux 9.4 x86_64
# 功能：以容器形式部署本项目 backend（FastAPI），复用共享基础设施
#       （/opt/deploy 下的 MariaDB 与 Nginx 容器，多项目复用、去项目前缀）；
#       H5 前端静态资源由共享 Nginx 托管；TLS 使用泛域名证书（acme.sh 自动续期）
# 项目仓库：https://github.com/wuzuniao/bai.git
#
# 使用方式：
#   1. 克隆仓库到服务器（本脚本位于仓库 scripts/ 目录下）
#   2. 确认共享基础设施就绪（/opt/deploy：mariadb 容器、泛域名证书
#      /opt/deploy/certs/wuzuniao.com.{pem,key}，由 acme.sh 统一管理）
#   3. 在项目根目录以 root 执行：bash scripts/deploy.sh
#   4. 可选环境变量：
#      INFRA_DIR=/opt/deploy                 # 共享基础设施目录
#      FORCE_FRONTEND_BUILD=1                # 强制重建 H5 前端（默认产物存在即跳过）
#      RESET_DB=1                            # 清空 MariaDB 数据目录重新初始化（危险！）
# ============================================================
set -e

# 脚本位于 git 仓库内（scripts/deploy.sh），clone_repo 的 git pull 会更新脚本自身；
# 先复制到临时文件执行，避免运行中文件被改写导致执行异常，结束后自动清理临时文件。
# 同时记录原始脚本目录（re-exec 后 BASH_SOURCE 会指向临时文件），用于推导项目根目录。
if [[ -z "${_DEPLOY_REEXEC:-}" ]]; then
  _deploy_orig_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  _deploy_tmp="$(mktemp /tmp/.deploy.XXXXXX.sh)"
  cp "${BASH_SOURCE[0]}" "$_deploy_tmp" && chmod +x "$_deploy_tmp"
  _DEPLOY_REEXEC=1 _DEPLOY_ORIG_DIR="$_deploy_orig_dir" exec bash "$_deploy_tmp" "$@"
fi
_deploy_self="${BASH_SOURCE[0]}"
trap 'rm -f "$_deploy_self"' EXIT

# ============== 可配置参数（按需修改） ==============
PYTHON_VERSION="3.11"            # Python 容器版本
MARIADB_VERSION="10.11"          # MariaDB LTS 版本
NGINX_IMAGE="nginx:stable"       # Nginx 镜像
NODE_VERSION="20"                # Node 版本（H5 前端构建用）

# Docker 镜像加速（Docker Hub 国内访问不稳定）
# 留空则自动配置 daemon.json 镜像加速器；填写则直接作为镜像前缀使用
# 例如：DOCKER_REGISTRY="docker.m.daocloud.io/library/"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"

# 项目根目录 = 脚本所在 scripts/ 的上一级，可被环境变量 INSTALL_DIR 覆盖。
# 脚本已不依赖硬编码路径，可移植到任意克隆位置；re-exec 后 BASH_SOURCE 指向
# 临时文件，故用 _DEPLOY_ORIG_DIR 还原原始脚本目录后再推导。
SCRIPT_DIR="${_DEPLOY_ORIG_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
INSTALL_DIR="${INSTALL_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"  # 项目克隆目录（会挂载到后端容器）
# 共享基础设施目录：MariaDB 与 Nginx 容器、各项目 backend 部署配置、站点配置、
# 证书、数据与备份均在此（多项目复用）；git 仓库目录仅保存项目源码
INFRA_DIR="${INFRA_DIR:-/opt/deploy}"
DEPLOY_DIR="${DEPLOY_DIR:-$INFRA_DIR/bai}"  # 本项目部署目录（仅 backend 容器的 compose，位于共享基础设施下）
REPO_URL="https://github.com/wuzuniao/bai.git"
BRANCH="main"

# GitHub 国内访问不稳定时使用的镜像源（按顺序尝试，留空则跳过）
# 也可通过环境变量 GITHUB_MIRROR 指定自定义镜像前缀
GITHUB_MIRRORS=(
  "https://gh-proxy.com"
  "https://ghproxy.net"
  "https://mirror.ghproxy.com"
)
# 若项目代码已手动上传到服务器，设置 LOCAL_PROJECT_DIR 指向其路径即可跳过克隆
# 例如：LOCAL_PROJECT_DIR=/tmp/bai bash scripts/deploy.sh
LOCAL_PROJECT_DIR="${LOCAL_PROJECT_DIR:-}"

DOMAIN="bai.wuzuniao.com"

DB_NAME_MAIN="wuzuniao_bai"       # 业务数据库
DB_USER="bai_backend"             # 后端数据库连接用户
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-}"  # 运行时自动生成
DB_PASSWORD="${DB_PASSWORD:-}"            # 运行时自动生成
# 若 MariaDB 数据目录存在旧数据导致 root 密码不匹配，设为 1 可清空数据目录重新初始化
# 警告：RESET_DB=1 会删除共享 MariaDB 数据目录（$INFRA_DIR/data/mariadb）下的全部数据！
RESET_DB="${RESET_DB:-0}"

# ============== 颜色与日志 ==============
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_step()  { echo -e "\n${BLUE}========== $* ==========${NC}"; }

# docker compose 辅助函数（在对应目录下执行，确保读取各自的 compose 与 .env）
dc() {
  (cd "$DEPLOY_DIR" && docker compose "$@")
}
dc_infra() {
  (cd "$INFRA_DIR" && docker compose "$@")
}

# ============== 1. 前置检查 ==============
check_prerequisites() {
  log_step "前置检查"

  if [[ $EUID -ne 0 ]]; then
    log_error "请以 root 用户运行此脚本"
    exit 1
  fi
  log_ok "当前为 root 用户"

  local arch
  arch=$(uname -m)
  if [[ "$arch" != "x86_64" ]]; then
    log_warn "当前架构为 $arch，本脚本面向 x86_64 环境"
  else
    log_ok "系统架构：x86_64"
  fi

  if [[ -f /etc/rocky-release ]]; then
    log_ok "操作系统：$(cat /etc/rocky-release)"
  else
    log_warn "未检测到 Rocky Linux，脚本基于 Rocky Linux 9.4 编写，可能不完全兼容"
  fi
}

# ============== 2. 安装 Docker 及基础工具 ==============
install_docker() {
  log_step "检查并安装 Docker 与基础工具"

  # 基础工具
  for pkg in git openssl unzip curl; do
    if ! command -v "$pkg" &>/dev/null; then
      log_info "安装 $pkg ..."
      dnf install -y "$pkg"
    fi
  done
  log_ok "基础工具已就绪"

  # Docker
  if command -v docker &>/dev/null; then
    log_ok "Docker 已安装：$(docker --version)"
  else
    log_info "安装 Docker CE ..."
    dnf install -y dnf-plugins-core
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
    log_ok "Docker 安装完成"
  fi

  systemctl is-active --quiet docker || systemctl start docker

  if docker compose version &>/dev/null; then
    log_ok "Docker Compose 可用：$(docker compose version)"
  else
    log_error "Docker Compose 插件不可用，请检查 docker-compose-plugin 安装"
    exit 1
  fi
}

# ============== 2.1 配置 Docker 镜像加速 ==============
setup_docker_mirror() {
  log_step "配置 Docker 镜像加速"

  # 如果用户指定了 DOCKER_REGISTRY，则直接使用该前缀，跳过 daemon.json 配置
  if [[ -n "$DOCKER_REGISTRY" ]]; then
    # 规范化：确保以 / 结尾
    [[ "$DOCKER_REGISTRY" != */ ]] && DOCKER_REGISTRY="${DOCKER_REGISTRY}/"
    log_ok "使用指定镜像前缀：$DOCKER_REGISTRY"
    return 0
  fi

  local daemon_json="/etc/docker/daemon.json"

  # 国内 Docker Hub 镜像加速器（按优先级排列）
  local mirrors
  if [[ -n "${DOCKER_MIRRORS:-}" ]]; then
    # 用户自定义镜像加速器（逗号分隔）
    IFS=',' read -ra mirrors <<< "$DOCKER_MIRRORS"
  else
    mirrors=(
      "https://docker.m.daocloud.io"
      "https://docker.1panel.live"
      "https://docker.unsee.tech"
      "https://docker.nju.edu.cn"
    )
  fi

  # 若已配置 registry-mirrors 则跳过
  if [[ -f "$daemon_json" ]] && grep -q "registry-mirrors" "$daemon_json" 2>/dev/null; then
    log_ok "daemon.json 已配置镜像加速器，跳过"
    return 0
  fi

  # 构建 JSON 镜像数组
  local mirror_json="["
  local first=true
  for m in "${mirrors[@]}"; do
    [[ "$first" == true ]] && first=false || mirror_json+=","
    mirror_json+="\"$m\""
  done
  mirror_json+="]"

  # 备份已有 daemon.json
  if [[ -f "$daemon_json" ]]; then
    cp "$daemon_json" "${daemon_json}.bak.$(date +%s)"
    log_info "已备份原 daemon.json"
  fi

  # 合并或创建 daemon.json
  if [[ -f "$daemon_json" ]] && command -v jq &>/dev/null; then
    jq --argjson m "$mirror_json" '. + {"registry-mirrors": $m}' "$daemon_json" > "${daemon_json}.tmp"
    mv "${daemon_json}.tmp" "$daemon_json"
  else
    cat > "$daemon_json" <<EOF
{
  "registry-mirrors": $mirror_json
}
EOF
  fi

  # 重启 Docker 生效
  systemctl restart docker
  sleep 3
  log_ok "Docker 镜像加速已配置并重启 Docker"
  log_info "加速器：${mirrors[*]}"
}

# ============== 2.2 预拉取容器镜像（带重试） ==============
pull_images() {
  log_step "预拉取容器镜像"

  local images=(
    "${DOCKER_REGISTRY}mariadb:${MARIADB_VERSION}"
    "${DOCKER_REGISTRY}python:${PYTHON_VERSION}-slim"
    "${DOCKER_REGISTRY}nginx:stable"
    "${DOCKER_REGISTRY}node:${NODE_VERSION}-slim"
  )

  for img in "${images[@]}"; do
    log_info "拉取 $img ..."
    local ok=false
    for i in 1 2 3; do
      if docker pull "$img" 2>&1; then
        log_ok "$img 拉取成功"
        ok=true
        break
      fi
      [[ $i -lt 3 ]] && log_warn "第 $i 次拉取失败，5 秒后重试 ..." && sleep 5
    done
    if [[ "$ok" != true ]]; then
      log_error "镜像 $img 拉取失败（已重试 3 次）"
      log_warn "请手动配置可用镜像源后重试："
      echo "  方式一：设置镜像前缀  DOCKER_REGISTRY=docker.m.daocloud.io/library/ bash scripts/deploy.sh"
      echo "  方式二：自定义加速器  DOCKER_MIRRORS=https://your-mirror.com bash scripts/deploy.sh"
      echo "  方式三：使用代理      export https_proxy=http://127.0.0.1:7890 && bash scripts/deploy.sh"
      exit 1
    fi
  done
}

# ============== 3. 配置防火墙 ==============
setup_firewall() {
  log_step "配置防火墙"

  if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
    log_ok "已开放 80/443 端口"
  else
    log_warn "firewalld 未运行，跳过防火墙配置（请确保 80/443 端口可访问）"
  fi
}

# ============== 4. 获取项目代码 ==============
clone_repo() {
  log_step "获取项目代码"

  # 优化 git 网络配置（缓解 SSL unexpected eof 问题）
  git config --global http.postBuffer 524288000  || true
  git config --global http.version HTTP/1.1      || true
  git config --global https.version HTTP/1.1     || true
  git config --global http.lowSpeedLimit 0       || true
  git config --global http.lowSpeedTime 999999   || true

  # --- 情况 A：项目目录已存在（.git 存在） ---
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    log_info "项目目录已存在，执行 git pull ..."
    git -C "$INSTALL_DIR" pull origin "$BRANCH" || log_warn "git pull 失败，使用现有代码继续"
    return 0
  fi

  # --- 情况 B：项目目录已有代码但无 .git（手动上传的代码） ---
  if [[ -n "$LOCAL_PROJECT_DIR" && -d "$LOCAL_PROJECT_DIR" ]]; then
    log_info "使用本地项目目录：$LOCAL_PROJECT_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    cp -a "$LOCAL_PROJECT_DIR" "$INSTALL_DIR"
    log_ok "项目代码已复制到 $INSTALL_DIR"
    return 0
  fi
  if [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/backend/run.py" ]]; then
    log_ok "检测到 $INSTALL_DIR 已有项目代码（无 .git），直接使用"
    return 0
  fi

  # --- 情况 C：从远程克隆 ---
  mkdir -p "$(dirname "$INSTALL_DIR")"

  # 构建克隆源列表：原始 URL + 镜像加速
  local clone_urls=("$REPO_URL")
  local mirror
  for mirror in "${GITHUB_MIRRORS[@]}"; do
    clone_urls+=("${mirror}/${REPO_URL}")
  done
  # 支持用户通过环境变量 GITHUB_MIRROR 指定自定义镜像
  if [[ -n "${GITHUB_MIRROR:-}" ]]; then
    clone_urls=("${GITHUB_MIRROR}/${REPO_URL}" "${clone_urls[@]}")
  fi

  local url idx=1 total=${#clone_urls[@]}
  for url in "${clone_urls[@]}"; do
    log_info "[$idx/$total] 尝试克隆：$url"
    if git clone -b "$BRANCH" --depth 1 "$url" "$INSTALL_DIR" 2>&1; then
      log_ok "项目克隆成功（来源：$url）"
      # 补全完整历史（可选，浅克隆已足够部署）
      git -C "$INSTALL_DIR" fetch --unshallow 2>/dev/null || true
      return 0
    fi
    log_warn "[$idx/$total] 克隆失败，尝试下一个源 ..."
    rm -rf "$INSTALL_DIR"
    idx=$((idx + 1))
    sleep 2
  done

  # --- 所有远程克隆均失败 ---
  log_error "所有克隆源均失败，网络无法访问 GitHub"
  echo ""
  log_warn "请选择以下任一方式手动上传项目代码后重新运行脚本："
  echo ""
  echo "  方式一：在可访问 GitHub 的机器上下载 zip，上传到服务器后解压"
  echo "    # 本地机器下载："
  echo "    wget https://github.com/wuzuniao/bai/archive/refs/heads/main.zip -O bai.zip"
  echo "    # 上传并解压到服务器："
  echo "    unzip bai.zip -d /opt/"
  echo "    mv /opt/bai-main /opt/bai"
  echo "    # 然后重新运行：bash scripts/deploy.sh"
  echo ""
  echo "  方式二：通过 scp/rsync 直接上传项目目录"
  echo "    scp -r bai/ root@SERVER:/opt/bai"
  echo "    # 然后重新运行：bash scripts/deploy.sh"
  echo ""
  echo "  方式三：指定自定义镜像或代理"
  echo "    GITHUB_MIRROR=https://your-mirror.com bash scripts/deploy.sh"
  echo "    # 或设置 http 代理："
  echo "    export https_proxy=http://127.0.0.1:7890"
  echo "    bash scripts/deploy.sh"
  echo ""
  exit 1
}

# ============== 5. 密码管理（支持重复执行） ==============
load_or_generate_passwords() {
  log_step "准备数据库密码"

  local compose_env="$INFRA_DIR/.env"
  local backend_env="$INSTALL_DIR/backend/.env"

  # root 密码：优先从 compose .env 读取
  if [[ -z "$DB_ROOT_PASSWORD" && -f "$compose_env" ]]; then
    DB_ROOT_PASSWORD=$(grep -E "^DB_ROOT_PASSWORD=" "$compose_env" 2>/dev/null | cut -d= -f2- || true)
  fi
  if [[ -z "$DB_ROOT_PASSWORD" ]]; then
    DB_ROOT_PASSWORD=$(openssl rand -hex 16)
    log_info "已生成新的 MariaDB root 密码"
  else
    log_info "复用已有的 MariaDB root 密码"
  fi

  # 后端用户密码：优先从 backend/.env 的 DATABASE_URL 中提取
  if [[ -z "$DB_PASSWORD" && -f "$backend_env" ]]; then
    DB_PASSWORD=$(grep -E "^DATABASE_URL=" "$backend_env" 2>/dev/null \
      | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p' || true)
  fi
  if [[ -z "$DB_PASSWORD" ]]; then
    DB_PASSWORD=$(openssl rand -hex 16)
    log_info "已生成新的后端数据库用户密码"
  else
    log_info "复用已有的后端数据库用户密码"
  fi
}

# ============== 6. 检查 HTTPS 证书（泛域名证书由 acme.sh 统一管理） ==============
setup_certs() {
  log_step "检查 HTTPS 证书"

  # 证书统一由 acme.sh 在共享基础设施目录签发与续期（wuzuniao.com + *.wuzuniao.com），
  # 本脚本不再自行生成/导入证书，仅校验其存在
  local cert_dir="$INFRA_DIR/certs"
  if [[ -f "$cert_dir/wuzuniao.com.pem" && -f "$cert_dir/wuzuniao.com.key" ]]; then
    log_ok "泛域名证书已就绪：$cert_dir/wuzuniao.com.{pem,key}"
    return 0
  fi

  log_error "未找到泛域名证书 $cert_dir/wuzuniao.com.{pem,key}"
  log_warn "证书由 acme.sh 统一管理（DNS 验证续期），请先在服务器上完成签发并安装到 $cert_dir，例如："
  echo "  /root/.acme.sh/acme.sh --install-cert -d wuzuniao.com --ecc \\"
  echo "    --fullchain-file $cert_dir/wuzuniao.com.pem \\"
  echo "    --key-file $cert_dir/wuzuniao.com.key \\"
  echo "    --reloadcmd 'docker exec nginx nginx -s reload'"
  exit 1
}

# ============== 7. 生成后端 Dockerfile ==============
generate_dockerfile() {
  log_step "生成后端 Dockerfile"

  cat > "$DEPLOY_DIR/Dockerfile.backend" <<'EOF'
FROM __REGISTRY__python:__PY_VER__-slim

ENV TZ=Asia/Shanghai
ENV PYTHONUNBUFFERED=1

# apt 换清华源（deb.debian.org 国内直连速率低），pip 同理用清华源
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# asyncmy 编译需要 gcc 与 MySQL 客户端开发库；curl 用于健康检查
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# 构建时安装 Python 依赖（运行时代码通过卷挂载提供）
# pip 国内镜像：服务器直连 PyPI 速率低（<100KB/s），使用清华源加速；如需官方源改为 https://pypi.org/simple
ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

EXPOSE 11001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "11001"]
EOF

  sed -i \
    -e "s|__REGISTRY__|$DOCKER_REGISTRY|g" \
    -e "s|__PY_VER__|$PYTHON_VERSION|g" \
    "$DEPLOY_DIR/Dockerfile.backend"
  log_ok "Dockerfile 已生成：$DEPLOY_DIR/Dockerfile.backend"
}

# ============== 8. 生成 Nginx 站点配置（写入共享基础设施目录） ==============
generate_nginx_conf() {
  log_step "生成 Nginx 站点配置（bai.conf）"

  # 站点配置统一放共享 nginx 的 conf.d 目录（/opt/deploy/nginx），放入即被加载
  mkdir -p "$INFRA_DIR/nginx"
  # 写入临时文件再替换占位符，最后用 cp 覆盖目标文件（保留 inode）
  # —— 避免 sed -i 更换 inode，导致运行中 nginx 容器的 bind mount 仍读到旧内容
  local _nginx_tmp="$INFRA_DIR/nginx/.bai.conf.tmp.$$"
  cat > "$_nginx_tmp" <<'EOF'
# bai.wuzuniao.com —— 古诗词学习业务（H5 前端静态 + 后端 API 反代）
# 说明：
#   - 由共享 nginx（/opt/deploy）统一承载 TLS 与反向代理
#   - 使用变量 + resolver 动态解析上游：bai-backend 未运行时 nginx 仍可正常启动（请求时 502）
#   - 证书为 wuzuniao.com 泛域名证书（acme.sh 自动续期，覆盖 *.wuzuniao.com）
#   - 本文件由 bai 服务的 scripts/deploy.sh 生成维护（幂等），手动修改请同步模板
#   - resolver 已统一在 00-resolver.conf 声明，站点配置内不可重复

# HTTP -> HTTPS 重定向
server {
    listen 80;
    server_name __DOMAIN__;
    return 301 https://$host$request_uri;
}

# HTTPS：H5 前端静态资源 + 后端 API/健康检查反向代理
server {
    listen 443 ssl;
    http2 on;
    server_name __DOMAIN__;

    ssl_certificate     /etc/nginx/certs/wuzuniao.com.pem;
    ssl_certificate_key /etc/nginx/certs/wuzuniao.com.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    client_max_body_size 20m;

    # gzip 压缩：HTML 由 gzip 模块默认压缩；此处补充 js/css/json/svg 等文本类型，
    # 传输体积降 60-70%，低带宽服务器上显著加快首屏；仅压缩 >1k 响应避免小响应浪费 CPU
    gzip on;
    gzip_vary on;
    gzip_comp_level 5;
    gzip_min_length 1024;
    gzip_types text/css text/javascript application/javascript application/json image/svg+xml application/xml text/plain;

    # H5 前端静态资源根目录（共享 nginx compose 挂载至 /var/www/bai）
    root /var/www/bai;
    index index.html;

    # 后端 API（路径保持不变：/api/v1/...）
    # 注意：X-Real-IP 与 X-Forwarded-For 是后端限流器（rate_limit.py）识别真实客户端 IP 的关键，
    #       缺失会导致限流被 X-Forwarded-For 伪造绕过。切勿删除以下两个 proxy_set_header。
    set $bai_upstream http://bai-backend:11001;

    location /api/ {
        proxy_pass $bai_upstream;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # 后端健康检查（路径保持不变：/health）
    location = /health {
        proxy_pass $bai_upstream;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # ===== H5 子目录部署（/h5/ 前缀，根路径保留给 Web 端）=====
    # 前端以 web.router.base=/h5/ 构建（frontend/manifest.json），产物仍挂载 /var/www/bai，
    # 以下 location 以 alias 去前缀映射到挂载点，产物零拷贝。
    # 注意：H5 页面内存在 /static 绝对路径引用（reader 图标等为运行时拼接，构建无法重写），
    # 故下方根路径 /static/ 规则保留兜底——Web 端上线时不得占用 /static 路径。

    # 带 hash 的构建产物（Vite 产物文件名即指纹）：永久缓存，内容更新时旧缓存自然失效
    location ^~ /h5/assets/ {
        alias /var/www/bai/assets/;
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        # 单连接限速：防爬虫（bingbot 等）并发抓取挤占带宽与 nginx worker，拖慢真实用户请求
        limit_rate 512k;
        try_files $uri =404;
    }

    # 入口页协商缓存（防发版后继续引用已清空的旧 bundle）；/h5/ 直接命中 index.html 时
    # 经 index 指令内部跳转到本块生效
    location = /h5/index.html {
        alias /var/www/bai/index.html;
        add_header Cache-Control "no-cache" always;
    }

    # 其余 /h5/ 路径（含 history 路由 /h5/pages/...）：静态命中，未命中回退入口页
    location ^~ /h5/ {
        alias /var/www/bai/;
        try_files $uri $uri/ /h5/index.html;
    }

    # 无尾斜杠补全，避免落入根路径 404 → 302 链
    location = /h5 {
        return 301 /h5/;
    }

    # uni-app static 目录兜底（页面内 /static 绝对引用打到域名根）：缓存 7 天，
    # 同名图片更新最多延迟 7 天可见（图标低频变更可接受），过期后经 ETag/Last-Modified
    # 协商返回 304
    location ^~ /static/ {
        add_header Cache-Control "public, max-age=604800" always;
        # 单连接限速：降低爬虫与恶意流量对出口带宽的挤占
        limit_rate 256k;
        try_files $uri =404;
    }

    # SPA 入口禁止强缓存（协商缓存）：每次发版浏览器都会拿到引用新 hash 资源的
    # 最新 index.html，根治「重新构建后页面未生效」——无 Cache-Control 时微信内置
    # 浏览器等会按启发式策略强缓存入口页，导致继续引用已被清空的旧 bundle（白屏/旧代码）
    location = /index.html {
        add_header Cache-Control "no-cache" always;
    }

    # robots.txt（SEO）：内联返回，无需静态文件；禁止爬虫抓取后端 API 与健康检查，
    # 页面路径默认允许收录（/h5/assets/ 下 JS/CSS 保持可抓取，供引擎渲染 SPA）
    location = /robots.txt {
        default_type text/plain;
        return 200 "User-agent: *\nDisallow: /api/\nDisallow: /health\nSitemap: https://bai.wuzuniao.com/sitemap.xml\n";
    }

    # sitemap.xml（SEO）：按惯例放域名根路径；文件随前端构建拷至 /static/sitemap.xml，
    # 此处 alias 映射，无需构建侧特殊处理
    location = /sitemap.xml {
        alias /var/www/bai/static/sitemap.xml;
        add_header Cache-Control "public, max-age=86400" always;
    }

    # 过渡期：域名根路径 302 至 /h5/（Web 端上线后以 Web 端站点配置替换本块）
    location = / {
        return 302 /h5/;
    }

    # 其余路径：静态资源优先命中，不存在的路径 302 跳转首页
    location / {
        try_files $uri $uri/ @not_found;
    }

    location @not_found {
        return 302 /;
    }
}
EOF

  sed -i "s/__DOMAIN__/$DOMAIN/g" "$_nginx_tmp"
  cp "$_nginx_tmp" "$INFRA_DIR/nginx/bai.conf"
  rm -f "$_nginx_tmp"
  # 清理旧版单文件站点配置（历史遗留，避免与新 bai.conf 重复定义 server）
  rm -f "$INFRA_DIR/nginx/default.conf"
  log_ok "Nginx 站点配置已生成：$INFRA_DIR/nginx/bai.conf"
}

# ============== 9. 生成 docker-compose.yml（仅 backend，接入共享网络） ==============
generate_compose_file() {
  log_step "生成 docker-compose.yml（backend）"

  # MariaDB 与 Nginx 由共享基础设施 compose（$INFRA_DIR）提供，
  # 本项目 compose 仅构建/运行自己的 backend 容器，经 app-net 网络互通
  cat > "$DEPLOY_DIR/docker-compose.yml" <<EOF
name: bai

services:
  backend:
    build:
      context: $INSTALL_DIR
      dockerfile: $DEPLOY_DIR/Dockerfile.backend
    container_name: bai-backend
    restart: unless-stopped
    volumes:
      # 以挂载本地目录方式将项目挂载到容器中运行
      - $INSTALL_DIR:/app:z
    working_dir: /app/backend
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "11001"]
    # 低资源服务器（约 1.8GB 内存）资源限制：防止单容器无限制占用内存触发整机 OOM/swap，
    # 拖累 mariadb/nginx/auth-backend 等共享基础设施。单 worker 事件循环已可处理高并发 IO。
    mem_limit: 512m
    mem_reservation: 256m
    cpus: 1.0
    # MariaDB 由共享基础设施提供，跨 compose 无法用 depends_on，
    # 后端应用启动时自带数据库连接重试
    networks:
      - app-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11001/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 40s
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "3"

# 接入共享基础设施网络（mariadb / nginx 由 $INFRA_DIR 提供）
networks:
  app-net:
    external: true
    name: app-net
EOF

  log_ok "docker-compose.yml 已生成：$DEPLOY_DIR/docker-compose.yml"
}


# ============== 10. 启动 MariaDB（共享基础设施） ==============
start_mariadb() {
  log_step "启动 MariaDB 容器（共享基础设施）"
  dc_infra up -d mariadb
  log_ok "MariaDB 容器已启动"
}

# ============== 12. 等待 MariaDB 就绪 ==============
# 注意：MariaDB 容器自带的 healthcheck.sh --connect 与 mysqladmin ping 都只检测
# 服务是否存活，不校验密码。当数据目录已有旧数据时，MARIADB_ROOT_PASSWORD 会被
# 忽略，容器仍显示 healthy，但用新密码连接会报 Access denied。
# 因此这里分两阶段：先等容器健康，再用 mysql -uroot -e "SELECT 1" 校验凭据。
wait_for_mariadb() {
  log_info "等待 MariaDB 容器变为 healthy ..."

  local max=60 i=0 health=""
  while [[ $i -lt $max ]]; do
    health=$(docker inspect --format='{{.State.Health.Status}}' mariadb 2>/dev/null || echo "")
    [[ "$health" == "healthy" ]] && break
    i=$((i + 1))
    sleep 2
  done

  if [[ "$health" != "healthy" ]]; then
    log_error "MariaDB 容器启动超时（120 秒未变为 healthy）"
    log_warn "请查看容器日志：docker logs mariadb"
    exit 1
  fi
  log_ok "MariaDB 容器已健康"

  verify_mariadb_credentials
}

# 校验 root 凭据；失败时根据 RESET_DB 决定重置数据目录还是退出
verify_mariadb_credentials() {
  log_info "校验 MariaDB root 凭据 ..."
  if docker exec -e MYSQL_PWD="$DB_ROOT_PASSWORD" mariadb \
      mysql -uroot -e "SELECT 1" &>/dev/null; then
    log_ok "MariaDB root 凭据校验通过"
    return 0
  fi

  log_warn "root 凭据校验失败（密码与现有数据目录不匹配）"

  local data_dir="$INFRA_DIR/data/mariadb"
  local has_stale_data=false
  if [[ -d "$data_dir" ]] && [[ -n "$(ls -A "$data_dir" 2>/dev/null)" ]]; then
    has_stale_data=true
  fi

  if [[ "$RESET_DB" == "1" ]]; then
    if [[ "$has_stale_data" == true ]]; then
      log_warn "RESET_DB=1：正在清空 MariaDB 数据目录并重新初始化 ..."
      log_warn "  清空目录：$data_dir （其中数据将丢失）"
      docker rm -f mariadb &>/dev/null || true
      rm -rf "${data_dir:?}/"* 2>/dev/null || true
      rm -rf "${data_dir:?}/".[!.]* 2>/dev/null || true
      dc_infra up -d mariadb
      # 等待重新初始化完成
      local j=0 h=""
      while [[ $j -lt 60 ]]; do
        h=$(docker inspect --format='{{.State.Health.Status}}' mariadb 2>/dev/null || echo "")
        [[ "$h" == "healthy" ]] && break
        j=$((j + 1))
        sleep 2
      done
      if [[ "$h" != "healthy" ]]; then
        log_error "重新初始化后 MariaDB 仍未就绪，请查看 docker logs mariadb"
        exit 1
      fi
      if docker exec -e MYSQL_PWD="$DB_ROOT_PASSWORD" mariadb \
          mysql -uroot -e "SELECT 1" &>/dev/null; then
        log_ok "重新初始化后 root 凭据校验通过"
        return 0
      fi
      log_error "重新初始化后凭据仍失败，请检查 docker logs mariadb"
      exit 1
    else
      # 数据目录为空但凭据失败：可能是初始化未完成，再多等一会
      log_warn "RESET_DB=1 但数据目录为空，继续等待初始化完成 ..."
      local k=0
      while [[ $k -lt 15 ]]; do
        sleep 2
        if docker exec -e MYSQL_PWD="$DB_ROOT_PASSWORD" mariadb \
            mysql -uroot -e "SELECT 1" &>/dev/null; then
          log_ok "MariaDB root 凭据校验通过"
          return 0
        fi
        k=$((k + 1))
      done
      log_error "MariaDB root 凭据持续校验失败，请查看 docker logs mariadb"
      exit 1
    fi
  fi

  # 未启用 RESET_DB：给出明确的重置指引
  log_error "MariaDB root 凭据校验失败，无法继续初始化数据库"
  echo ""
  log_warn "原因：MariaDB 数据目录已有旧数据，忽略了 MARIADB_ROOT_PASSWORD 环境变量"
  log_warn "      （mysqladmin ping / healthcheck.sh --connect 只检测服务存活，不校验密码）"
  echo ""
  log_warn "解决方案（任选其一）："
  echo "  方式一（推荐，清空旧数据库重新初始化）："
  echo "    RESET_DB=1 bash scripts/deploy.sh"
  echo ""
  echo "  方式二（手动清理后重跑）："
  echo "    docker compose -f $INFRA_DIR/docker-compose.yml down"
  echo "    rm -rf $data_dir/*"
  echo "    bash scripts/deploy.sh"
  echo ""
  echo "  方式三（若记得旧 root 密码，复用旧密码继续）："
  echo "    DB_ROOT_PASSWORD='旧密码' bash scripts/deploy.sh"
  echo ""
  exit 1
}

# ============== 13. 初始化数据库（建库 + 建表） ==============
init_databases() {
  log_step "初始化数据库"

  local sql_dir="$INSTALL_DIR/backend/sql"

  # 幂等检查：若业务库已有表则跳过
  local table_count
  table_count=$(docker exec -e MYSQL_PWD="$DB_ROOT_PASSWORD" mariadb \
    mysql -uroot -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$DB_NAME_MAIN'" 2>/dev/null || echo 0)

  if [[ "$table_count" -gt 0 ]]; then
    log_info "数据库 $DB_NAME_MAIN 已有表结构，跳过 SQL 导入"
    return 0
  fi

  # 导入业务库
  if [[ -f "$sql_dir/create_bai_db.sql" ]]; then
    log_info "导入 $DB_NAME_MAIN 数据库结构与表 ..."
    docker exec -i -e MYSQL_PWD="$DB_ROOT_PASSWORD" mariadb \
      mysql -uroot < "$sql_dir/create_bai_db.sql"
    log_ok "$DB_NAME_MAIN 导入完成"
  else
    log_warn "未找到 $sql_dir/create_bai_db.sql，跳过"
  fi
  # 用户库 wuzuniao_yonghu 已归 auth 服务（其 scripts/deploy.sh 负责建库与授权），此处不再导入
}

# ============== 14. 创建后端专用数据库用户 ==============
create_db_user() {
  log_step "创建后端数据库连接用户"

  docker exec -i -e MYSQL_PWD="$DB_ROOT_PASSWORD" mariadb mysql -uroot <<EOF
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';
ALTER USER '$DB_USER'@'%' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON $DB_NAME_MAIN.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
EOF

  # 用户库 wuzuniao_yonghu 权限已移除（数据库拆分：用户库仅 auth 服务的 auth_backend 用户可连）
  log_ok "后端用户 '$DB_USER' 已创建并授予 $DB_NAME_MAIN 权限"
}

# ============== 15. 生成后端 .env（更新数据库连接到环境变量） ==============
generate_backend_env() {
  log_step "生成后端环境变量配置"

  local env_file="$INSTALL_DIR/backend/.env"

  # 保留已有的 微信 / auth / COS 配置（若 .env 已存在）
  local wx_appid="" wx_secret="" auth_token=""
  local cos_secret_id="" cos_secret_key="" cos_bucket="" cos_region="" cos_appid="" cos_custom_domain=""
  local project_name="" api_v1=""
  if [[ -f "$env_file" ]]; then
    project_name=$(grep -E "^PROJECT_NAME=" "$env_file" 2>/dev/null | cut -d= -f2- || true)
    api_v1=$(grep -E "^API_V1_STR="         "$env_file" 2>/dev/null | cut -d= -f2- || true)
    wx_appid=$(grep -E "^WX_APPID="             "$env_file" 2>/dev/null | cut -d= -f2- || true)
    wx_secret=$(grep -E "^WX_APP_SECRET="       "$env_file" 2>/dev/null | cut -d= -f2- || true)
    auth_token=$(grep -E "^AUTH_SERVICE_TOKEN=" "$env_file" 2>/dev/null | cut -d= -f2- || true)
    cos_secret_id=$(grep -E "^COS_SECRET_ID="         "$env_file" 2>/dev/null | cut -d= -f2- || true)
    cos_secret_key=$(grep -E "^COS_SECRET_KEY="       "$env_file" 2>/dev/null | cut -d= -f2- || true)
    cos_bucket=$(grep -E "^COS_BUCKET="               "$env_file" 2>/dev/null | cut -d= -f2- || true)
    cos_region=$(grep -E "^COS_REGION="               "$env_file" 2>/dev/null | cut -d= -f2- || true)
    cos_appid=$(grep -E "^COS_APPID="                 "$env_file" 2>/dev/null | cut -d= -f2- || true)
    cos_custom_domain=$(grep -E "^COS_CUSTOM_DOMAIN=" "$env_file" 2>/dev/null | cut -d= -f2- || true)
    cp "$env_file" "${env_file}.bak.$(date +%s)"
    log_info "已备份原 .env，并保留 微信 / auth / COS 配置"
  fi

  # 项目基本信息：与 .env.example / config.py 字段对齐，缺失时填代码默认值
  : "${project_name:=无足鸟古诗词学习助手}"
  : "${api_v1:=/api/v1}"
  : "${cos_region:=ap-guangzhou}"

  # 服务间通信令牌：复用已有令牌 → 回读 auth 服务 .env 的 SERVICE_TOKEN → 新生成
  # （跨服务自动对齐：auth 侧部署脚本同样回读本服务 .env，任一先部署均收敛为同一令牌；
  #   auth 仓库默认克隆于 /opt/auth，不同路径时用 AUTH_INSTALL_DIR 显式指定）
  if [[ -z "$auth_token" ]]; then
    local auth_backend_env="${AUTH_INSTALL_DIR:-/opt/auth}/backend/.env"
    if [[ -f "$auth_backend_env" ]]; then
      auth_token=$(grep -E "^SERVICE_TOKEN=" "$auth_backend_env" 2>/dev/null | cut -d= -f2- || true)
      [[ -n "$auth_token" ]] && log_info "已从 auth 服务的 backend/.env 同步服务间通信令牌"
    fi
  fi
  if [[ -z "$auth_token" ]]; then
    auth_token=$(openssl rand -hex 32)
    log_info "已生成新的 AUTH_SERVICE_TOKEN（auth 侧部署时将自动回读对齐）"
  fi

  # DATABASE_URL 使用后端专用用户连接 mariadb 容器（服务名 mariadb）
  local db_url="mysql+asyncmy://${DB_USER}:${DB_PASSWORD}@mariadb:3306/${DB_NAME_MAIN}?charset=utf8mb4"

  cat > "$env_file" <<EOF
# ============================================================
# 后端环境变量（由部署脚本自动生成）
# 生成时间：$(date '+%Y-%m-%d %H:%M:%S')
# ============================================================
# 项目名称（FastAPI 文档标题等展示用途）
PROJECT_NAME=${project_name}
# API 路由前缀（一般无需修改）
API_V1_STR=${api_v1}

# 数据库连接（使用后端专用用户，连接 mariadb 容器服务名）
DATABASE_URL=${db_url}

# 微信小程序配置（登录侧凭证由 auth 服务持有同一对；AppSecret 仅存后端，严禁下发前端）
WX_APPID=${wx_appid}
WX_APP_SECRET=${wx_secret}

# auth 统一认证服务配置（用户模块已独立部署）
AUTH_BASE_URL=https://auth.wuzuniao.com
AUTH_ISSUER=https://auth.wuzuniao.com
AUTH_SERVICE_TOKEN=${auth_token}
AUTH_CLIENT_ID=bai
REVOCATION_SYNC_INTERVAL_SECONDS=300

# 腾讯云 COS 对象存储（书籍文件云端同步；SecretId/Key 留空则云端同步接口不可用）
COS_SECRET_ID=${cos_secret_id}
COS_SECRET_KEY=${cos_secret_key}
COS_BUCKET=${cos_bucket}
COS_REGION=${cos_region}
COS_APPID=${cos_appid}
COS_CRED_SECONDS=1800
COS_CUSTOM_DOMAIN=${cos_custom_domain}

# CORS 跨域配置（本地开发源由 main.py 的 allow_origin_regex 统一放行）
CORS_ALLOW_ORIGINS=https://bai.wuzuniao.com
EOF

  chmod 600 "$env_file"
  log_ok "后端 .env 已生成：$env_file"
  log_info "DATABASE_URL 用户：$DB_USER  →  连接 mariadb:3306/$DB_NAME_MAIN"
  log_info "服务间令牌：$(echo "$auth_token" | cut -c1-8)…（回读自 auth 服务 .env；缺失时请检查 auth 部署）"
}

# ============== 16. 构建 H5 前端（已存在则跳过，节省资源） ==============
build_frontend() {
  log_step "构建 H5 前端"

  local frontend_dir="$INSTALL_DIR/frontend"
  local h5_dist="$frontend_dir/dist/build/h5"

  if [[ ! -f "$frontend_dir/package.json" ]]; then
    log_warn "未找到 $frontend_dir/package.json，跳过 H5 前端构建"
    return 0
  fi

  # 构建产物已存在则跳过（npm 构建消耗 CPU/内存较大；需强制重建时设 FORCE_FRONTEND_BUILD=1）
  if [[ "$FORCE_FRONTEND_BUILD" != "1" && -f "$h5_dist/index.html" ]]; then
    log_ok "检测到已有构建产物 $h5_dist，跳过前端构建（FORCE_FRONTEND_BUILD=1 可强制重建）"
    return 0
  fi

  local node_image="${DOCKER_REGISTRY}node:${NODE_VERSION}-slim"
  # 国内 npm 直连慢，默认使用 npmmirror 镜像；可用环境变量 NPM_REGISTRY 覆盖
  local npm_registry="${NPM_REGISTRY:-https://registry.npmmirror.com}"
  local npm_ci_args="install --no-audit --no-fund --legacy-peer-deps --force"
  [[ -n "$npm_registry" ]] && npm_ci_args="$npm_ci_args --registry=$npm_registry"

  log_info "使用 $node_image 构建 H5（npm $npm_ci_args && npm run build:h5）..."
  log_info "资源限制：memory=1g swap=2g cpus=1.5"

  # 在 Node 容器内构建，产物通过卷挂载写回宿主机 frontend/dist/build/h5
  # 低内存服务器资源限制（防止单容器无限制占用触发整机 OOM/swap）：
  #   --memory=1g --memory-swap=2g --cpus=1.5；NODE_OPTIONS 另限 node 堆 768MB
  docker run --rm \
    --memory=1g \
    --memory-swap=2g \
    --cpus=1.5 \
    -v "$frontend_dir:/app:z" \
    -e NODE_OPTIONS="--max-old-space-size=768" \
    -w /app \
    "$node_image" \
    sh -c "npm $npm_ci_args && npm run build:h5"

  if [[ ! -f "$h5_dist/index.html" ]]; then
    log_error "H5 构建失败：未找到 $h5_dist/index.html"
    log_warn "可手动在 $frontend_dir 执行：npm install && npm run build:h5 后重试"
    exit 1
  fi

  log_ok "H5 前端构建完成：$h5_dist"
}

# ============== 17. 构建并启动后端，并确保共享 Nginx 加载本站点 ==============
start_backend_nginx() {
  log_step "构建并启动后端容器"
  dc up -d --build backend
  log_ok "后端容器已启动"

  # 共享 nginx（/opt/deploy）启动或热重载，使 bai.conf 站点生效
  if docker ps --format '{{.Names}}' | grep -q "^nginx$"; then
    if docker exec nginx nginx -t >/dev/null 2>&1; then
      docker exec nginx nginx -s reload && log_ok "共享 nginx 已热重载，$DOMAIN 站点配置生效"
    else
      log_warn "nginx 配置校验未通过，请检查 $INFRA_DIR/nginx/bai.conf"
    fi
  else
    dc_infra up -d nginx
    log_ok "共享 nginx 容器已启动（加载 $INFRA_DIR/nginx/ 全部站点配置）"
  fi
}

# ============== 18. 验证部署 ==============
verify_deployment() {
  log_step "验证部署"

  # 等待后端健康
  log_info "等待后端服务就绪 ..."
  local max=30 i=0
  while [[ $i -lt $max ]]; do
    if docker exec bai-backend curl -sf http://localhost:11001/health &>/dev/null; then
      log_ok "后端健康检查通过 /health → {\"status\":\"ok\"}"
      break
    fi
    i=$((i + 1))
    sleep 2
  done
  if [[ $i -ge $max ]]; then
    log_warn "后端健康检查未通过，请查看日志：docker logs bai-backend"
  fi

  # Nginx 配置检查
  if docker exec nginx nginx -t &>/dev/null; then
    log_ok "Nginx 配置语法正确"
  else
    log_warn "Nginx 配置检查失败，请查看日志：docker logs nginx"
  fi

  # H5 前端可访问性检查
  log_info "验证 H5 前端 ..."
  if docker exec nginx test -f /var/www/bai/index.html 2>/dev/null; then
    log_ok "H5 静态资源已挂载（/var/www/bai/index.html 存在）"
  else
    log_warn "未在 nginx 容器中找到 H5 首页，请检查前端构建与卷挂载"
  fi
  if curl -sk -o /dev/null -w '%{http_code}' -H "Host: $DOMAIN" "https://127.0.0.1/h5/" 2>/dev/null | grep -q 200; then
    log_ok "H5 首页可访问（HTTPS 200，/h5/）"
  else
    log_warn "H5 首页访问异常，请查看 docker logs nginx"
  fi

  echo ""
  log_info "容器运行状态："
  docker ps --filter "name=bai-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# ============== 19. 输出部署摘要 ==============
print_summary() {
  echo ""
  echo -e "${GREEN}================================================${NC}"
  echo -e "${GREEN}  Bai 部署完成（后端 + H5 前端）${NC}"
  echo -e "${GREEN}================================================${NC}"
  cat <<EOF

  项目目录：       $INSTALL_DIR
  本项目部署目录： $DEPLOY_DIR（仅 backend 容器）
  共享基础设施：   $INFRA_DIR（mariadb / nginx 容器、站点配置、证书、数据、备份）

  数据库信息：
    MariaDB 版本：    $MARIADB_VERSION
    业务数据库：      $DB_NAME_MAIN（用户库 wuzuniao_yonghu 已归 auth 服务）
    后端连接用户：    $DB_USER（独立项目用户，仅授权本库）
    后端用户密码：    $DB_PASSWORD
    root 密码：       $DB_ROOT_PASSWORD

  容器服务：
    MariaDB  →  mariadb  (共享，内部 3306，仅本机可访问)
    Backend  →  bai-backend  (本项目专属，内部 11001，经 app-net 网络互通)
    H5 前端  →  共享 Nginx 静态托管（构建产物 frontend/dist/build/h5 → /var/www/bai，经 /h5/ 前缀访问，根路径保留给 Web 端）
    Nginx    →  nginx  (共享，对外 80/443，反代 /api/、/health 至后端)

  访问地址：
    H5 前端：        https://$DOMAIN/h5/
    健康检查：        https://$DOMAIN/health
    API 入口：        https://$DOMAIN/api/v1

  常用命令（在 $DEPLOY_DIR 下执行）：
    查看后端日志：    docker logs -f bai-backend
    重启后端：        docker compose restart
    停止后端：        docker compose down
    查看运行状态：    docker compose ps
    共享基础设施：    cd $INFRA_DIR && docker compose ps

  注意事项：
    1. 请在 $INSTALL_DIR/backend/.env 中确认微信小程序配置（WX_APPID/WX_APP_SECRET）已填写
    2. root 密码保存在 $INFRA_DIR/.env，后端用户密码保存在 $INSTALL_DIR/backend/.env
    3. 更新代码：cd $INSTALL_DIR && git pull，然后 cd $DEPLOY_DIR && docker compose restart backend
    4. 如遇 SELinux 导致的挂载问题，可执行 setenforce 0 临时关闭后重试
    5. 更新 H5 前端代码后，FORCE_FRONTEND_BUILD=1 bash scripts/deploy.sh 强制重建（默认跳过已有构建产物）
    6. auth 统一认证服务（同机部署）已由共享 nginx 统一承载 auth.wuzuniao.com（检测到其部署时自动生成站点配置）；
       服务间令牌 AUTH_SERVICE_TOKEN 已自动与 auth 侧对齐（任一先部署均收敛为同一令牌）
    7. 泛域名证书由 acme.sh 自动续期并热重载共享 nginx，全站子域名均自动覆盖

EOF
}

# ============== 主流程 ==============
main() {
  echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${BLUE}║   Bai 后端一键部署脚本  (Rocky Linux 9.4)   ║${NC}"
  echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"

  check_prerequisites
  install_docker
  setup_docker_mirror
  setup_firewall
  clone_repo

  # 创建部署目录结构（本项目部署目录 + 共享基础设施目录）
  mkdir -p "$DEPLOY_DIR" "$INFRA_DIR"/{nginx,certs,data/mariadb}

  load_or_generate_passwords
  setup_certs
  generate_dockerfile
  generate_nginx_conf
  generate_compose_file

  # 预拉取镜像（在启动容器前确保镜像可用）
  pull_images

  start_mariadb
  wait_for_mariadb
  init_databases
  create_db_user
  generate_backend_env

  build_frontend
  start_backend_nginx
  verify_deployment
  print_summary
}

main "$@"

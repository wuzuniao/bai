#!/usr/bin/env bash
# ============================================================
# 脚本名称：backup_db.sh
# 功能：备份 MariaDB 共享容器（mariadb）内的业务数据库
#       - wuzuniao_bai（古诗词学习助手业务库）
#
#       共享 MariaDB 内其他库的备份职责：
#       - wuzuniao_yao     → yao  服务 scripts/backup_db.sh（每周一 00:00）
#       - wuzuniao_yonghu  → auth 服务 scripts/backup_db.sh（每周一 00:30）
#       - wuzuniao_jin     → jin  服务 scripts/backup_db.sh（每周一 01:30）
#
# 备份要求：
#   1. 数据库单独一个 .sql 文件
#   2. 包含完整的 CREATE DATABASE / CREATE TABLE 结构
#   3. 数据以单行 INSERT 方式插入（--skip-extended-insert）
#   4. 文件按 日期_库名.sql 命名，保存到 /opt/deploy/data/backup_sql 目录
#   5. 数据库仅保留最近 12 份备份，超出自动清理
#
# 定时任务：每周一 01:00 执行（cron: 0 1 * * 1）
# ============================================================
set -euo pipefail

# ===== 路径推导（使用 BASH_SOURCE 保持可移植性）=====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="/opt/deploy"
BACKUP_DIR="$DEPLOY_DIR/data/backup_sql"
ENV_FILE="$DEPLOY_DIR/.env"

# ===== 配置 =====
CONTAINER_NAME="mariadb"
DATABASES=("wuzuniao_bai")
DATE="$(date +%Y-%m-%d)"
MAX_BACKUPS=12          # 每个数据库保留的最近备份数

# ===== 日志函数 =====
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# ===== 读取数据库 root 密码 =====
if [[ ! -f "$ENV_FILE" ]]; then
    log "错误：找不到环境变量文件 $ENV_FILE"
    exit 1
fi
DB_ROOT_PASSWORD="$(grep -E "^DB_ROOT_PASSWORD=" "$ENV_FILE" | head -1 | cut -d= -f2-)"
if [[ -z "$DB_ROOT_PASSWORD" ]]; then
    log "错误：$ENV_FILE 中未找到 DB_ROOT_PASSWORD"
    exit 1
fi

# ===== 创建备份目录 =====
mkdir -p "$BACKUP_DIR"

# ===== 检查容器是否运行 =====
if ! docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -q true; then
    log "错误：容器 $CONTAINER_NAME 未运行"
    exit 1
fi

# ===== 执行备份 =====
SUCCESS_COUNT=0
FAIL_COUNT=0

for DB in "${DATABASES[@]}"; do
    BACKUP_FILE="$BACKUP_DIR/${DATE}_${DB}.sql"
    log "开始备份数据库：$DB -> $BACKUP_FILE"

    # --databases             包含 CREATE DATABASE IF NOT EXISTS 和 USE 语句
    # --single-transaction    InnoDB 一致性快照，不锁表
    # --default-character-set 保证 utf8mb4 字符集正确导出
    # --complete-insert       INSERT 语句包含列名，提升恢复兼容性
    # --skip-extended-insert  每行数据一条 INSERT 语句（单行插入）
    # --routines --triggers --events  包含存储过程/触发器/事件（完整备份）
    if docker exec "$CONTAINER_NAME" mariadb-dump \
        --databases "$DB" \
        --single-transaction \
        --default-character-set=utf8mb4 \
        --complete-insert \
        --skip-extended-insert \
        --routines \
        --triggers \
        --events \
        -uroot -p"$DB_ROOT_PASSWORD" \
        > "$BACKUP_FILE" 2>/dev/null; then

        if [[ -s "$BACKUP_FILE" ]]; then
            chmod 600 "$BACKUP_FILE"
            SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            log "备份成功：$DB（大小：$SIZE）"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        else
            log "备份失败：$DB（输出文件为空）"
            rm -f "$BACKUP_FILE"
            FAIL_COUNT=$((FAIL_COUNT + 1))
        fi
    else
        log "备份失败：$DB（mariadb-dump 返回错误）"
        rm -f "$BACKUP_FILE"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
done

# ===== 清理旧备份（每个数据库仅保留最近 MAX_BACKUPS 份）=====
for DB in "${DATABASES[@]}"; do
    # 文件名以日期开头，ls 默认升序排列即为从旧到新
    # head -n -N 输出除最后 N 行外的所有行（即最早的超出部分）
    DELETE_LIST=$(ls -1 "$BACKUP_DIR"/*_"$DB".sql 2>/dev/null | head -n -"$MAX_BACKUPS" || true)
    if [[ -n "$DELETE_LIST" ]]; then
        while IFS= read -r OLD_FILE; do
            rm -f "$OLD_FILE"
            log "已清理旧备份：$(basename "$OLD_FILE")"
        done <<< "$DELETE_LIST"
    fi
done

log "备份完成：成功 $SUCCESS_COUNT 个，失败 $FAIL_COUNT 个"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    exit 1
fi

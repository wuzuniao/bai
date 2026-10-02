-- =============================================================
-- 无足鸟古诗词学习助手（bai）业务库建库脚本
-- 说明：
-- 1. 仅表结构、不含数据行；幂等可重放（CREATE DATABASE / TABLE 均带 IF NOT EXISTS）
-- 2. 用户与认证相关数据一律归 auth 服务（wuzuniao_yonghu 库），
--    本库禁止创建用户表，禁止存储令牌、密码哈希等认证凭证
-- 3. 业务表随业务功能迭代在本文件追加；增量变更同步追加 add_*.sql 并回填本脚本
-- =============================================================

CREATE DATABASE IF NOT EXISTS `wuzuniao_bai`
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `wuzuniao_bai`;

-- （当前无业务表：业务功能落地时在此追加建表语句）

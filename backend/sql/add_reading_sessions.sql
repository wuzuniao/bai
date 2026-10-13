-- =============================================================
-- 阅读会话流水增量表结构
-- 说明：
-- 1. 幂等可重放（IF NOT EXISTS）；已同步回填 create_bai_db.sql
-- 2. 定位：按书/时段的明细账（按书统计、阅读习惯分析用）；
--    时长聚合真源仍是 reading_daily_stats（档位判定/今日已读），
--    离线补传的会话发生时未登录未计 daily_stats，两账不保证一致
-- 3. 口径与时长统计一致：minutes 向下取整，<1 分钟不入账（客户端不产生）；
--    started_at/ended_at 为客户端本地时刻（设备时区按东八区约定）
-- 4. 书籍删除时会话流水保留（阅读历史属用户而非书籍）；book_title 为落库时快照，
--    删书后按书统计仍能展示书名（孤儿 book_id 记录以快照为准，不依赖书籍行存在）
-- =============================================================

USE `wuzuniao_bai`;

CREATE TABLE IF NOT EXISTS `reading_sessions` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL COMMENT '业务用户 id（JWT sub）',
  `book_id` BIGINT NOT NULL COMMENT '书籍 id（user_books.id；删书后保留孤儿行）',
  `book_title` VARCHAR(200) NOT NULL DEFAULT '' COMMENT '书名快照（落库时从 user_books.title 取，删书后按书统计展示用）',
  `source` VARCHAR(10) NOT NULL DEFAULT 'txt' COMMENT '阅读器类型 txt / pdf',
  `started_at` DATETIME NOT NULL COMMENT '会话起算时刻（客户端本地时刻）',
  `ended_at` DATETIME NOT NULL COMMENT '会话结算时刻',
  `minutes` INT NOT NULL DEFAULT 0 COMMENT '会话分钟数（向下取整，与时长统计口径一致）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY `idx_rs_user_book` (`user_id`, `book_id`),
  KEY `idx_rs_user_started` (`user_id`, `started_at`)
) COMMENT='阅读会话流水（按书/时段明细账）';

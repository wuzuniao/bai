-- =============================================================
-- 增量：阅读业务元数据五张表（2026-10-11）
-- 说明：书籍正文不落库，后端仅保存元数据；同步回填 create_bai_db.sql
-- 幂等：全部 CREATE TABLE IF NOT EXISTS，可重放
-- =============================================================

USE `wuzuniao_bai`;

-- 1. 用户书籍元数据（同用户书名唯一，重导入同名书复用同一行实现跨设备按书名关联）
CREATE TABLE IF NOT EXISTS `user_books` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL COMMENT '业务用户 id（JWT sub）',
  `title` VARCHAR(200) NOT NULL COMMENT '书名（导入时取文件名去扩展名；同用户内唯一，跨设备按书名关联进度与笔记）',
  `author` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '作者（本地导入暂无，预留）',
  `format` VARCHAR(10) NOT NULL COMMENT 'TXT / PDF（重导入同书换格式时更新）',
  `size` BIGINT NOT NULL DEFAULT 0 COMMENT '文件字节数（重导入时回填）',
  `chapter_count` INT NOT NULL DEFAULT 0 COMMENT '章节数（txt=解析章数含序章；PDF=页数；重导入时回填）',
  `has_preface` TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'txt 序章存在性（导入时固化，重导入时回填）',
  `sort_order` INT NOT NULL DEFAULT 0 COMMENT '书架手动排序（越小越前）',
  `last_read_at` DATETIME NULL COMMENT '最近阅读时刻（NULL=未读）',
  `last_chapter` INT NOT NULL DEFAULT -1 COMMENT '最近章 id（-1=未读；PDF 恒 -1）',
  `last_page_index` INT NOT NULL DEFAULT 0 COMMENT '章内页码 0-based（txt 恢复定位）',
  `last_scroll_top` INT NOT NULL DEFAULT 0 COMMENT '滚动模式滚动位置 px（txt 恢复定位）',
  `last_percent` INT NOT NULL DEFAULT 0 COMMENT '阅读百分比 0-100（仅 PDF 用）',
  `pdf_ratio` DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT 'PDF 首页高/宽比（页面布局参数）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_ub_user_title` (`user_id`, `title`),
  KEY `idx_user_books_lastread` (`user_id`, `last_read_at`)
) COMMENT='用户书籍元数据';

-- 2. 阅读划线与想法（合一：note_type 区分）
CREATE TABLE IF NOT EXISTS `reading_notes` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `book_id` BIGINT NOT NULL COMMENT '所属书籍（user_books.id，应用层级联）',
  `note_type` TINYINT(1) NOT NULL COMMENT '0=划线 1=想法',
  `cid` INT NOT NULL DEFAULT 0 COMMENT '划线章 id（type=0；type=1 置 0）',
  `origin` INT NOT NULL DEFAULT 0 COMMENT '划线段索引（type=0；type=1 置 0）',
  `ranges` JSON NULL COMMENT '段内字符闭区间 [[start,end],...]（type=0 专用）',
  `from_cid` INT NOT NULL DEFAULT 0 COMMENT '选区起点章 id（type=1；type=0 置 0）',
  `from_origin` INT NOT NULL DEFAULT 0 COMMENT '选区起点段（type=1）',
  `from_start` INT NOT NULL DEFAULT 0 COMMENT '选区起点字符（type=1）',
  `to_cid` INT NOT NULL DEFAULT 0 COMMENT '选区终点章 id（type=1）',
  `to_origin` INT NOT NULL DEFAULT 0 COMMENT '选区终点段（type=1）',
  `to_end` INT NOT NULL DEFAULT 0 COMMENT '选区终点字符（type=1）',
  `quote` TEXT NULL COMMENT '划线文本快照（type=1）',
  `content` TEXT NULL COMMENT '想法正文（type=1；type=0 为 NULL）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY `idx_rn_user_book` (`user_id`, `book_id`, `note_type`, `cid`, `origin`)
) COMMENT='阅读划线与想法（合一）';

-- 3. 阅读书签
CREATE TABLE IF NOT EXISTS `reading_bookmarks` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `book_id` BIGINT NOT NULL COMMENT '所属书籍（user_books.id，应用层级联）',
  `chapter_id` INT NOT NULL COMMENT '章 id',
  `page_index` INT NOT NULL DEFAULT 0 COMMENT '章内页码 0-based',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_rb_pos` (`user_id`, `book_id`, `chapter_id`, `page_index`),
  KEY `idx_rb_user_book` (`user_id`, `book_id`)
) COMMENT='阅读书签';

-- 4. 每日阅读时长统计
CREATE TABLE IF NOT EXISTS `reading_daily_stats` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `stat_date` DATE NOT NULL COMMENT '统计日期（东八区）',
  `minutes` INT NOT NULL DEFAULT 0 COMMENT '当日累计阅读分钟数',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_rds_user_date` (`user_id`, `stat_date`)
) COMMENT='每日阅读时长统计';

-- 5. 用户阅读偏好（单行 JSON）
CREATE TABLE IF NOT EXISTS `user_preferences` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL COMMENT '业务用户 id（JWT sub）',
  `prefs` JSON NOT NULL COMMENT '偏好配置（reader_settings：字号/翻页/主题/字体；bookshelf_style：白卡/深灰）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_up_user` (`user_id`)
) COMMENT='用户阅读偏好';

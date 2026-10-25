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

-- =============================================================
-- 阅读业务表（书籍正文文件不落库，仅存用户端沙盒；后端只保存元数据）
-- =============================================================

-- 1. 用户书籍元数据（书架列表 + 阅读进度恢复的唯一数据源；同用户书名唯一，重导入同名书复用同一行实现跨设备按书名关联）
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

-- 2. 阅读划线与想法（合一：note_type 区分；划线=章+段+区间集合，想法=跨章选区+文本快照+正文）
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
  KEY `idx_rn_user_book` (`user_id`, `book_id`, `note_type`, `cid`, `origin`),
  KEY `idx_rn_user_created` (`user_id`, `created_at`)
) COMMENT='阅读划线与想法（合一）';

-- 3. 阅读书签（纯定位记录，与笔记语义分立）
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

-- 4. 每日阅读时长统计（书架统计卡与总阅读时长；按日 upsert 累加）
CREATE TABLE IF NOT EXISTS `reading_daily_stats` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `stat_date` DATE NOT NULL COMMENT '统计日期（东八区）',
  `minutes` INT NOT NULL DEFAULT 0 COMMENT '当日累计阅读分钟数（按日封顶 1440）',
  `last_report_at` DATETIME NULL COMMENT '节奏校验锚点：最近一次受理时长上报的服务器时刻（NULL=尚无上报）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_rds_user_date` (`user_id`, `stat_date`)
) COMMENT='每日阅读时长统计';

-- 5. 用户阅读偏好（单行 JSON：阅读设置 字号/翻页/主题/字体 + 书架卡片样式）
CREATE TABLE IF NOT EXISTS `user_preferences` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL COMMENT '业务用户 id（JWT sub）',
  `prefs` JSON NOT NULL COMMENT '偏好配置（reader_settings：字号/翻页/主题/字体；bookshelf_style：白卡/深灰）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_up_user` (`user_id`)
) COMMENT='用户阅读偏好';

-- =============================================================
-- 活动奖励表（货币 / 签到 / 阅读档位；业务规则见 app/services/reward_service.py 常量）
-- =============================================================

-- 6. 货币账户（金银铜余额；铜/银满 100 自动进位，余额恒 0-99）
CREATE TABLE IF NOT EXISTS `coin_accounts` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL COMMENT '业务用户 id（JWT sub）',
  `copper` INT NOT NULL DEFAULT 0 COMMENT '铜币余额（进位后恒 0-99）',
  `silver` INT NOT NULL DEFAULT 0 COMMENT '银币余额（进位后恒 0-99）',
  `gold` INT NOT NULL DEFAULT 0 COMMENT '金币余额',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_ca_user` (`user_id`)
) COMMENT='货币账户（金银铜余额）';

-- 7. 货币流水（全部金银铜变动明细；「今日已获铜币」=当日 checkin/reading 铜币入账汇总）
CREATE TABLE IF NOT EXISTS `coin_transactions` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `coin_type` TINYINT(1) NOT NULL COMMENT '币种 0=铜 1=银 2=金',
  `amount` INT NOT NULL COMMENT '变动量（正=入账 负=扣减；自动兑换产生成对增减流水）',
  `source` VARCHAR(32) NOT NULL COMMENT '来源 checkin=每日签到 / reading=阅读档位奖励 / exchange=自动兑换 / consume=商城消费',
  `source_id` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '来源单据 id（签到/领取记录 id；兑换为空）',
  `remark` VARCHAR(100) NOT NULL DEFAULT '' COMMENT '变动说明',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_ct_user_time` (`user_id`, `created_at`)
) COMMENT='货币流水';

-- 8. 每日签到记录（一人一日一行；连续天数由本周记录推导，不落冗余字段；
--    会员补签行 is_makeup=1，奖励按被补日星期基准档发放）
CREATE TABLE IF NOT EXISTS `checkin_records` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `checkin_date` DATE NOT NULL COMMENT '签到日期（东八区）',
  `reward` INT NOT NULL DEFAULT 0 COMMENT '发放铜币数（按星期定档）',
  `is_makeup` TINYINT NOT NULL DEFAULT 0 COMMENT '是否补签 0=正常签到 1=会员补签（奖励按被补日星期基准档）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_cr_user_date` (`user_id`, `checkin_date`)
) COMMENT='每日签到记录';

-- 9. 阅读档位奖励领取记录（按日按档唯一：达成后随分钟上报自动发放，余额变动不影响领取状态、不重复发放）
CREATE TABLE IF NOT EXISTS `reading_reward_claims` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `claim_date` DATE NOT NULL COMMENT '达成统计日期（东八区）',
  `tier_minutes` INT NOT NULL COMMENT '档位阈值分钟数（5/30/120/360/720）',
  `reward` INT NOT NULL DEFAULT 0 COMMENT '发放铜币数（基础+额外赠送）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_rrc_user_date_tier` (`user_id`, `claim_date`, `tier_minutes`)
) COMMENT='阅读时长档位奖励领取记录';

-- 10. 阅读会话流水（按书/时段明细账；时长聚合真源仍是 reading_daily_stats，离线补传场景两账不保证一致；
--     口径与时长统计一致：minutes 向下取整，<1 分钟不入账；书籍删除时会话流水保留，
--     book_title 为落库时书名快照，删书后按书统计仍能展示书名）
CREATE TABLE IF NOT EXISTS `reading_sessions` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL COMMENT '业务用户 id（JWT sub）',
  `book_id` BIGINT NOT NULL COMMENT '书籍 id（user_books.id；删书后保留孤儿行）',
  `book_title` VARCHAR(200) NOT NULL DEFAULT '' COMMENT '书名快照（落库时从 user_books.title 取）',
  `source` VARCHAR(10) NOT NULL DEFAULT 'txt' COMMENT '阅读器类型 txt / pdf',
  `started_at` DATETIME NOT NULL COMMENT '会话起算时刻（客户端本地时刻）',
  `ended_at` DATETIME NOT NULL COMMENT '会话结算时刻',
  `minutes` INT NOT NULL DEFAULT 0 COMMENT '会话分钟数（向下取整，与时长统计口径一致）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY `idx_rs_user_book` (`user_id`, `book_id`),
  KEY `idx_rs_user_started` (`user_id`, `started_at`)
) COMMENT='阅读会话流水（按书/时段明细账）';

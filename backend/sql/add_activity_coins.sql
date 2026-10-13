-- =============================================================
-- 活动奖励（货币 / 签到 / 阅读档位）增量表结构
-- 说明：
-- 1. 幂等可重放（均带 IF NOT EXISTS）；已同步回填 create_bai_db.sql
-- 2. 业务规则（后端常量为准）：
--    - 签到奖励：周一~周五 +5 铜币固定；周六/周日按本周（周一~昨日）
--      漏签天数顺延递减：周六漏 ≥1 天降至 +5（满勤 +10）；周日漏 0 天 +20、
--      漏 1 天 +10、漏 ≥2 天 +5 保底（checkin_records.reward 落实际发放额）；
--      自然周口径（周一~周日），断签后连续天数从缺口次日重计
--    - 阅读档位（按日独立领取）：5'=+1、30'=+6、120'=+24+赠10、
--      360'=+72+赠30、720'=+144+赠60
--    - 自动兑换：铜满 100 进 1 银、银满 100 进 1 金（发放时服务端自动进位，
--      产生成对增减流水）
--    - 领取记录按 (user, date, tier) 唯一：余额被兑换/消费扣除后
--      不影响当日领取状态，不会随阅读时长重复发放
-- =============================================================

USE `wuzuniao_bai`;

-- 1. 货币账户（金银铜余额；铜/银满 100 自动进位，余额恒 0-99）
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

-- 2. 货币流水（全部金银铜变动明细；「今日已获铜币」=当日 checkin/reading 铜币入账汇总）
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

-- 3. 每日签到记录（一人一日一行；连续天数由本周记录推导，不落冗余字段）
CREATE TABLE IF NOT EXISTS `checkin_records` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `user_id` BIGINT NOT NULL,
  `checkin_date` DATE NOT NULL COMMENT '签到日期（东八区）',
  `reward` INT NOT NULL DEFAULT 0 COMMENT '发放铜币数（按星期定档）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_cr_user_date` (`user_id`, `checkin_date`)
) COMMENT='每日签到记录';

-- 4. 阅读档位奖励领取记录（按日按档唯一：达成后手动领取，余额变动不影响领取状态、不重复发放）
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

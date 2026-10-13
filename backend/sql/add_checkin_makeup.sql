-- ======================================================
-- 增量脚本：会员补签（2026-10-13）
-- 幂等：可重复执行
-- 背景：黑铁及以上会员每月（自然月）可补签 3 次——补签在
--       checkin_records 插入被补日期行（is_makeup=1，奖励按被补日
--       星期基准档发放，连续天数推导自动包含）；
--       会员身份按令牌 roles 声明本地判定（含 iron/bronze/silver/gold/admin），
--       月度限额按补签操作时刻所在自然月计数
-- ======================================================

USE `wuzuniao_bai`;

-- ------------------------------------------------------
-- checkin_records 增加 is_makeup（存量行默认 0=正常签到，不受影响）
-- ------------------------------------------------------
ALTER TABLE `checkin_records`
  ADD COLUMN IF NOT EXISTS `is_makeup` TINYINT NOT NULL DEFAULT 0 COMMENT '是否补签 0=正常签到 1=会员补签（奖励按被补日星期基准档）';

-- 列注释更正（补签语义改为发放奖励口径；MODIFY 幂等无害）
ALTER TABLE `checkin_records`
  MODIFY COLUMN `is_makeup` TINYINT NOT NULL DEFAULT 0 COMMENT '是否补签 0=正常签到 1=会员补签（奖励按被补日星期基准档）';

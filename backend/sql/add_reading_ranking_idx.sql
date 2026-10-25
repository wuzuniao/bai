-- =============================================================
-- 阅读时长排行聚合走覆盖索引（2026-10）：reading_daily_stats 补 (stat_date, user_id, minutes)
-- /reading/ranking 按 stat_date 区间对全体用户 group by user_id 求和，
-- 既有 uk_rds_user_date 前缀为 user_id 无法命中该查询；本索引使聚合为索引扫描，
-- 不再随流水表线性增长退化为全表扫描
-- 幂等可重放（MariaDB CREATE INDEX IF NOT EXISTS）
-- =============================================================
CREATE INDEX IF NOT EXISTS `idx_rds_date_user`
    ON `reading_daily_stats` (`stat_date`, `user_id`, `minutes`);

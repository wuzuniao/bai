-- =============================================================
-- 阅读报告笔记数统计走索引（2026-10）：reading_notes 补 (user_id, created_at)
-- 统计页 /reading/report 的笔记数按 user_id + created_at 区间计数，
-- 既有 idx_rn_user_book 前缀仅 user_id，会扫该用户全部笔记行
-- 幂等可重放（MariaDB CREATE INDEX IF NOT EXISTS）
-- =============================================================
CREATE INDEX IF NOT EXISTS `idx_rn_user_created`
    ON `reading_notes` (`user_id`, `created_at`);

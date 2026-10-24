-- =============================================================
-- 阅读时长防刷（2026-10）：reading_daily_stats 增加节奏校验锚点列
-- 配套服务端口径见 app/services/reading_service.py（按日封顶 1440 + 节奏校验）
-- 幂等可重放（MariaDB ADD COLUMN IF NOT EXISTS）
-- =============================================================
ALTER TABLE `reading_daily_stats`
    ADD COLUMN IF NOT EXISTS `last_report_at` DATETIME NULL
    COMMENT '节奏校验锚点：最近一次受理时长上报的服务器时刻（NULL=尚无上报）'
    AFTER `minutes`;

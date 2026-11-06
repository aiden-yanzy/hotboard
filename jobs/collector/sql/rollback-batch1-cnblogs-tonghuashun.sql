-- 回滚第一批补源：只停增量，不删历史（items 有外键，DELETE 会级联清历史）
BEGIN;
UPDATE sources SET enabled=false, updated_at=now()
 WHERE engine='custom' AND src_id IN ('cnblogs','tonghuashun');
COMMIT;

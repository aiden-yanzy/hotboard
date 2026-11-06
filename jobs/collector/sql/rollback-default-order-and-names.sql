-- 回滚排序/名称：sort_order 清空（回到按 name 排序），名称按适配器 NAME 复原
BEGIN;
UPDATE sources SET sort_order=NULL WHERE engine='custom';
COMMIT;

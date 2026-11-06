-- 回滚分类：按适配器 CATEGORY 复原（购物 1 + 财经 1，其余见适配器文件）
BEGIN;
UPDATE sources SET category='购物' WHERE engine='custom' AND src_id='smzdm';
UPDATE sources SET category='财经' WHERE engine='custom' AND src_id='tonghuashun';
UPDATE sources SET category='综合' WHERE engine='custom' AND src_id IN
  ('xueqiu','wallstreetcn','cls','jin10','cankaoxiaoxi');
COMMIT;

-- 参照站 rebang.today 对照后的第一批补源（2026-10-19）
-- 看板：博客园(cnblogs)、同花顺(tonghuashun)。适配器已单独实测通过（21 条 / 100 条带热度）。
BEGIN;
INSERT INTO sources (id, engine, src_id, name, category, enabled) VALUES
  ('custom:cnblogs',    'custom', 'cnblogs',    '博客园',     '开发', true),
  ('custom:tonghuashun','custom', 'tonghuashun','同花顺热榜', '财经', true)
ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, category=EXCLUDED.category, enabled=true;
COMMIT;

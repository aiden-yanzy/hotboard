-- 参照站对照第二批（2026-10-19）：机核 / 量子位 / 开源中国（适配器已单独实测通过）
-- 说明：酷安(coolapk) 适配器已按 MIT 移植写好，但实测 HTTP 403（上游 DailyHotApi 同样失败）
--       → 保留代码、暂不注册启用；等有可用 cookie/签名方案再开。
BEGIN;
INSERT INTO sources (id, engine, src_id, name, category, enabled) VALUES
  ('custom:gcores',  'custom', 'gcores',  '机核',     '娱乐', true),
  ('custom:qbitai',  'custom', 'qbitai',  '量子位',   '科技', true),
  ('custom:oschina', 'custom', 'oschina', '开源中国', '开发', true)
ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, category=EXCLUDED.category, enabled=true;
COMMIT;

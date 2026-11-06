-- ============================================================
-- 源清单修正（2026-10-12 工程化 · 增源 A 收尾）—— 幂等，可重复执行
-- ------------------------------------------------------------
-- 背景：启用 newsnow 引擎后逐源探测（`GET /api/s?id=<id>`），发现三类问题：
--   ① **id 写错**：newsnow 的 36氪快讯 id 是 `36kr`（不是 `_36kr`）、Steam 是 `steam`（不是 `steammkt`）
--        实测：?id=_36kr → HTTP 500；?id=36kr → 200 / 20 条；?id=steammkt → 500；?id=steam → 200 / 30 条
--   ② **上游坏**：`pcbeta`(远景)、`smzdm` 在 newsnow 侧恒返 HTTP 500
--        （dailyhot 侧的 smzdm 正常 → 只停 newsnow 那一行，不停用整站）
--   ③ **新发现可用源**（此前未接入）：`cls`(财联社) / `producthunt` / `hackernews`
--        （dailyhot 侧 hackernews 一直拿不到数据，newsnow 侧 30 条/轮 → 互补成功）
--
-- 安全说明：items.source_id 外键 references sources(id)，**没有** on update cascade
--   → 改源 id 必须「插新行 → 搬 items → 删旧行」，不能直接 update 主键。
-- ============================================================
begin;

-- ---------- ① 修正写错的引擎侧 id（36氪快讯）----------
insert into sources (id, engine, src_id, name, category, enabled)
select 'newsnow:36kr', 'newsnow', '36kr', '36kr', coalesce(category, '科技'), true
  from sources where id = 'newsnow:_36kr'
on conflict (id) do nothing;
update items set source_id = 'newsnow:36kr' where source_id = 'newsnow:_36kr';
delete from sources where id = 'newsnow:_36kr';

-- ---------- ① 修正写错的引擎侧 id（Steam 市场）----------
insert into sources (id, engine, src_id, name, category, enabled)
select 'newsnow:steam', 'newsnow', 'steam', 'steam', coalesce(category, '购物'), true
  from sources where id = 'newsnow:steammkt'
on conflict (id) do nothing;
update items set source_id = 'newsnow:steam' where source_id = 'newsnow:steammkt';
delete from sources where id = 'newsnow:steammkt';

-- ---------- ② 上游恒 500 的 newsnow 源停用 ----------
update sources
   set enabled = false,
       last_err = 'newsnow 上游 HTTP 500（2026-10-12 实测，且 dailyhot 侧已有同源）'
 where id in ('newsnow:pcbeta', 'newsnow:smzdm');

-- ---------- ③ 新接入源（经实测可用）----------
insert into sources (id, engine, src_id, name, category, enabled) values
  ('newsnow:cls',         'newsnow', 'cls',         'cls',         '综合', true),   -- 财联社
  ('newsnow:hackernews',  'newsnow', 'hackernews',  'hackernews',  '开发', true),   -- Hacker News
  ('newsnow:producthunt', 'newsnow', 'producthunt', 'producthunt', '科技', true)    -- Product Hunt
on conflict (id) do nothing;

commit;

-- 校验：
--   select engine, enabled, count(*) from sources group by 1,2 order by 1,2;
--   select name, category, enabled from sources where id in
--     ('newsnow:36kr','newsnow:steam','newsnow:cls','newsnow:hackernews','newsnow:producthunt','newsnow:pcbeta','newsnow:smzdm');

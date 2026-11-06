-- ⭐ 2026-10-22 Step 1：current_items 物化「当前榜单」
-- 背景：API 每次请求都要算「该源最新一批」（原先是相关子查询，微博源 1290 次重算 ≈ 5s）。
--   这里把「每个源当前榜单」物化到一张小表，由采集器**每轮按源整体替换**，
--   读路径变成一次索引扫描（2~5ms，零 join）。
-- 回滚：drop table current_items;

create table if not exists current_items (
  source_id text        not null references sources(id) on delete cascade,
  item_id   bigint      not null,
  rank      integer,
  heat      bigint,
  ts        timestamptz not null,          -- 这批榜单的时间戳（= snapshots.ts）
  title     text        not null,
  url       text,
  ext_id    text,
  meta      jsonb,
  primary key (source_id, item_id)
);

create index if not exists idx_current_source_rank on current_items (source_id, rank);

-- 回填：每个源取「最新一批」快照
insert into current_items (source_id, item_id, rank, heat, ts, title, url, ext_id, meta)
select i.source_id, i.id, sn.rank, sn.heat, sn.ts, i.title, i.url, i.ext_id, i.meta
from (
  select i2.source_id, max(sn2.ts) as ts
  from snapshots sn2
  join items i2 on i2.id = sn2.item_id
  group by i2.source_id
) l
join items i on i.source_id = l.source_id
join snapshots sn on sn.item_id = i.id and sn.ts = l.ts
on conflict (source_id, item_id) do update
  set rank  = excluded.rank,
      heat  = excluded.heat,
      ts    = excluded.ts,
      title = excluded.title,
      url   = excluded.url,
      meta  = excluded.meta;

analyze current_items;

-- 热榜平台库表（P2，2026-10-22 与线上结构对齐）
-- 设计要点：
--   1) sources 表是「源的唯一真源」：engine/enabled 决定采不采，下线某引擎只改这里
--   2) items 靠 (source_id, url_hash) 去重 → 同源同一条永远一行，last_seen 往后推
--   3) snapshots 记每轮 rank/heat → 「涨跌/趋势」的唯一依据
--      ⭐ 2026-10-22：改为**按月 RANGE 分区**；保留策略靠 DROP PARTITION（O(1)，不膨胀）
--   4) current_items = 「每个源当前这一批」的物化表，采集器每轮按源整体替换
--      → API 读当前榜单零 join、毫秒级（原先扫 140 万行 snapshots 算 max(ts)，实测 5 秒）
--   5) title_sim 预留跨源同题合并（真正合并交给 LLM 聚簇，规则硬合并易误伤）
--   6) hotboard_maintain()：采集器每天调一次（补未来分区 + 删 90 天前分区 + 清 180 天老 items）

create table if not exists sources (
  id          text primary key,            -- 'dailyhot:zhihu' / 'newsnow:jin10' / 'custom:zhihu'
  engine      text not null,               -- 'dailyhot' | 'newsnow' | 'custom'
  src_id      text not null,               -- 引擎内的源 id（用于拼请求）
  name        text,
  category    text,
  enabled     boolean not null default true,
  last_ok_at  timestamptz,
  last_err    text,
  items_seen  integer not null default 0,  -- 最近一轮抓到的条数（健康观测）
  updated_at  timestamptz not null default now(),
  sort_order  integer                      -- 手工排序（API 只按它排，前端不覆盖）
);
create index if not exists idx_sources_engine on sources (engine, enabled);
-- 同一引擎内 src_id 必须唯一：原来只有主键 id 约束，换个 name 就能再插一行，
-- 历史上就是这么攒出 61 行 dailyhot/newsnow 残留的（见 docs/部署.md「分类与源清单」）
create unique index if not exists uq_sources_engine_src on sources (engine, src_id);

create table if not exists items (
  id          bigserial primary key,
  source_id   text not null references sources(id) on delete cascade,
  ext_id      text,
  title       text not null,
  url         text,
  url_hash    char(64) not null,
  title_sim   char(16),
  first_seen  timestamptz not null default now(),
  last_seen   timestamptz not null default now(),
  meta        jsonb,
  unique (source_id, url_hash)
);
create index if not exists idx_items_title_sim on items (title_sim);
create index if not exists idx_items_last_seen on items (last_seen desc);
create index if not exists idx_items_source_seen on items (source_id, last_seen desc);

-- ---------- snapshots：按月分区 ----------
create table if not exists snapshots (
  item_id  bigint not null references items(id) on delete cascade,
  ts       timestamptz not null,
  rank     int,
  heat     bigint,
  primary key (item_id, ts)          -- 分区表主键必须含分区键
) partition by range (ts);

-- 建表时自动补「上 2 个月 ~ 未来 4 个月」的分区（幂等：新环境 / 换月都不用手工建）
do $$
declare
  m    date := (date_trunc('month', now())::date - interval '2 months')::date;
  stop date := (date_trunc('month', now())::date + interval '4 months')::date;
begin
  while m < stop loop
    if not exists (select 1 from pg_class
                    where relname = 'snapshots_p_' || to_char(m, 'YYYYMM')) then
      execute format(
        'create table snapshots_p_%s partition of snapshots for values from (%L) to (%L)',
        to_char(m, 'YYYYMM'), m, (m + interval '1 month')::date);
    end if;
    m := (m + interval '1 month')::date;
  end loop;
end $$;

create index if not exists idx_snap2_item_ts on snapshots (item_id, ts desc);
create index if not exists idx_snap2_ts on snapshots (ts desc);

-- ---------- current_items：每源当前批次（物化表，采集器每轮替换） ----------
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

-- 采集运行日志（每轮一行）：用于"这轮采了多少、哪个引擎挂了"
create table if not exists crawl_runs (
  id          bigserial primary key,
  started_at  timestamptz not null,
  finished_at timestamptz,
  engine_stats jsonb,
  items_new   integer default 0,
  items_upd   integer default 0,
  snapshots   integer default 0,
  errors      integer default 0
);

-- 源级限流冷却（被站点打回时指数退避，冷却期内跳过）
create table if not exists source_backoff (
  source_id  text primary key,
  until      timestamptz not null,
  level      integer not null default 1,
  reason     text,
  updated_at timestamptz not null default now()
);

-- ---------- 保留策略（采集器每天调一次） ----------
create or replace function hotboard_maintain(keep_days int default 90,
                                             items_days int default 180)
returns table(action text, detail text) language plpgsql as $$
declare
  m date;
  p record;
  n int;
begin
  -- a) 未来 3 个月的分区补齐
  for i in 0..3 loop
    m := (date_trunc('month', now())::date + (i || ' month')::interval)::date;
    if not exists (select 1 from pg_class where relname = 'snapshots_p_' || to_char(m, 'YYYYMM')) then
      execute format(
        'create table snapshots_p_%s partition of snapshots for values from (%L) to (%L)',
        to_char(m, 'YYYYMM'), m, (m + interval '1 month')::date);
      return query select 'create_partition', to_char(m, 'YYYY-MM');
    end if;
  end loop;

  -- b) 删掉上界早于 keep_days 的分区
  for p in
    select c.relname
    from pg_class c
    join pg_inherits i on i.inhrelid = c.oid
    where i.inhparent = 'snapshots'::regclass
      and c.relname like 'snapshots_p_%'
  loop
    begin
      if to_date(substr(p.relname, 13, 6) || '01', 'YYYYMMDD')
         + interval '1 month' < now() - (keep_days || ' days')::interval then
        execute format('drop table %I', p.relname);
        return query select 'drop_partition', p.relname;
      end if;
    exception when others then
      null;
    end;
  end loop;

  -- c) 清理长期没再出现过的 items
  delete from items where last_seen < now() - (items_days || ' days')::interval;
  get diagnostics n = row_count;
  return query select 'delete_stale_items', n::text;
end $$;

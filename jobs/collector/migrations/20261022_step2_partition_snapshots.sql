-- ⭐ 2026-10-22 Step 2：snapshots 按月分区 + 保留策略
--
-- 背景：snapshots 已 142 万行 / 175MB，按当前速度 ~11.7 万行/天增长。
--   不分区的话清理旧数据只能 DELETE（千万行级会留下大量死元组，表反而更大、vacuum 压力大）。
--   改成按月 RANGE 分区后，清理 = DROP PARTITION（O(1)，无膨胀）。
--
-- 用法：
--   psql -f 20261022_step2_partition_snapshots.sql      # 一次性迁移（会短暂锁表，先停采集）
--   select hotboard_maintain();                          # 之后的日常维护（建未来分区+删旧分区+清老 items）
--
-- 回滚：
--   alter table snapshots rename to snapshots_part;
--   alter table snapshots_old rename to snapshots;
--   drop table snapshots_part;

begin;

-- 1) 新分区表（结构同 snapshots；主键必须含分区键 ts）
create table snapshots_p (
  item_id bigint      not null references items(id) on delete cascade,
  ts      timestamptz not null,
  rank    integer,
  heat    bigint,
  primary key (item_id, ts)
) partition by range (ts);

-- 2) 先把历史覆盖到的月份分区建出来（2026-07 ~ 2027-03）
do $$
declare
  m date := date_trunc('month', (select min(ts) from snapshots)::date)::date;
  stop date := (date_trunc('month', now())::date + interval '4 months')::date;
begin
  while m < stop loop
    execute format(
      'create table snapshots_p_%s partition of snapshots_p for values from (%L) to (%L)',
      to_char(m, 'YYYYMM'), m, (m + interval '1 month')::date);
    m := (m + interval '1 month')::date;
  end loop;
end $$;

-- 3) 拷数据（必须在建 default 分区之前，否则会全落进 default）
insert into snapshots_p (item_id, ts, rank, heat) select item_id, ts, rank, heat from snapshots;

-- 4) 换表
alter table snapshots rename to snapshots_old;
alter table snapshots_p rename to snapshots;

commit;

-- 5) 索引（分区表上建会自动下发到每个分区）
-- ⚠️ 索引名不能复用旧表的：snapshots_old 仍持有 idx_snap_item_ts / idx_snapshots_ts，
--    用同名 + if not exists 会「静默跳过」→ 新分区表根本没索引（这个坑 2026-10-22 踩过一次）
create index if not exists idx_snap2_item_ts on snapshots (item_id, ts desc);
create index if not exists idx_snap2_ts on snapshots (ts desc);
analyze snapshots;

-- 6) 日常维护函数：建未来分区 + 删旧分区 + 清老 items
create or replace function hotboard_maintain(keep_days int default 90,
                                             items_days int default 180)
returns table(action text, detail text) language plpgsql as $$
declare
  m date;
  p record;
  n int;
begin
  -- a) 未来 3 个月的分区补齐
  m := date_trunc('month', now())::date;
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
    -- 从分区名解析出月份上界
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

  -- c) 清理长期没再出现过的 items（其 snapshots 已随分区清理或级联删除）
  delete from items where last_seen < now() - (items_days || ' days')::interval;
  get diagnostics n = row_count;
  return query select 'delete_stale_items', n::text;
end $$;

-- 7) 校验：行数应与迁移前一致（142 万级）
select (select count(*) from snapshots) as snapshots_rows,
       (select count(*) from snapshots_old) as old_rows;

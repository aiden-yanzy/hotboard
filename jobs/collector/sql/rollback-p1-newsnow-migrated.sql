-- P1 回滚：把已迁移站点的 newsnow 侧重新启用（2026-10-19 生成）
-- 背景：这些站点已由 engine='custom' 的自研适配器接管，newsnow 侧停用是为消除双路重复
-- 变更记录见 docs/抓取逻辑规范化-执行记录.md 第六节
update sources set enabled=true where id='newsnow:cankaoxiaoxi';  -- cankaoxiaoxi
update sources set enabled=true where id='newsnow:cls';  -- cls
update sources set enabled=true where id='newsnow:dongqiudi';  -- dongqiudi
update sources set enabled=true where id='newsnow:douban';  -- douban
update sources set enabled=true where id='newsnow:freebuf';  -- freebuf
update sources set enabled=true where id='newsnow:ifeng';  -- ifeng
update sources set enabled=true where id='newsnow:jin10';  -- jin10
update sources set enabled=true where id='newsnow:nowcoder';  -- nowcoder
update sources set enabled=true where id='newsnow:producthunt';  -- producthunt
update sources set enabled=true where id='newsnow:solidot';  -- solidot
update sources set enabled=true where id='newsnow:steam';  -- steam
update sources set enabled=true where id='newsnow:wallstreetcn';  -- wallstreetcn
update sources set enabled=true where id='newsnow:xueqiu';  -- xueqiu

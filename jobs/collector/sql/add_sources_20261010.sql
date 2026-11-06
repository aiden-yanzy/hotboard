-- 2026-10-10 补源：上游 dailyhot-api 有、但我们 sources 表里从没登记过的源
-- 背景：config.yml 的 bootstrap 只登记了 31 个源 → 上游其余 19 个可用源一直没进库
-- 可用性实测（http://127.0.0.1:6688/<src>）：19 个有数据；gameres 返回空；
--   coolapk/earthquake/hostloc/linuxdo/producthunt 被源站墙（HTTP 500）→ 不登记
-- 回滚：delete from sources where id like 'dailyhot:%' and src_id in (...新增列表...);
insert into sources (id, engine, src_id, name, category, enabled) values
  ('dailyhot:51cto',          'dailyhot', '51cto',          '51cto',          '开发',     true),
  ('dailyhot:douban-movie',   'dailyhot', 'douban-movie',   'douban-movie',   '社区',     true),
  ('dailyhot:douyin',         'dailyhot', 'douyin',         'douyin',         '综合',     true),
  ('dailyhot:genshin',        'dailyhot', 'genshin',        'genshin',        '游戏娱乐', true),
  ('dailyhot:github',         'dailyhot', 'github',         'github',         '开发',     true),
  ('dailyhot:hackernews',     'dailyhot', 'hackernews',     'hackernews',     '科技',     true),
  ('dailyhot:history',        'dailyhot', 'history',        'history',        '综合',     true),
  ('dailyhot:honkai',         'dailyhot', 'honkai',         'honkai',         '游戏娱乐', true),
  ('dailyhot:ithome-xijiayi', 'dailyhot', 'ithome-xijiayi', 'ithome-xijiayi', '游戏娱乐', true),
  ('dailyhot:lol',            'dailyhot', 'lol',            'lol',            '游戏娱乐', true),
  ('dailyhot:miyoushe',       'dailyhot', 'miyoushe',       'miyoushe',       '游戏娱乐', true),
  ('dailyhot:newsmth',        'dailyhot', 'newsmth',        'newsmth',        '社区',     true),
  ('dailyhot:nytimes',        'dailyhot', 'nytimes',        'nytimes',        '综合',     true),
  ('dailyhot:qq-news',        'dailyhot', 'qq-news',        'qq-news',        '综合',     true),
  ('dailyhot:sina',           'dailyhot', 'sina',           'sina',           '综合',     true),
  ('dailyhot:sina-news',      'dailyhot', 'sina-news',      'sina-news',      '综合',     true),
  ('dailyhot:starrail',       'dailyhot', 'starrail',       'starrail',       '游戏娱乐', true),
  ('dailyhot:weatheralarm',   'dailyhot', 'weatheralarm',   'weatheralarm',   '综合',     true),
  ('dailyhot:zhihu-daily',    'dailyhot', 'zhihu-daily',    'zhihu-daily',    '综合',     true)
on conflict (id) do nothing;

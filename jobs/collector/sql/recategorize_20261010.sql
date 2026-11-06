-- 2026-10-10 分类重做：按源重新归类（原「综合」17 个源太杂，混了热搜/门户/生活服务）
-- 新方案 9 个分类：热点 / 新闻媒体 / 科技 / 开发 / 社区 / 游戏 / 娱乐 / 生活 / 购物
--
-- 回滚（旧分类）：
--   update sources set category='综合' where src_id in ('baidu','douyin','history','hupu','kuaishou',
--     'netease-news','nytimes','qq-news','sina','sina-news','thepaper','tieba','toutiao',
--     'weatheralarm','weibo','zhihu','zhihu-daily');
--   update sources set category='科技' where src_id in ('36kr','dgtle','geekpark','guokr','hackernews','huxiu','ifanr','ithome','sspai');
--   update sources set category='开发' where src_id in ('51cto','52pojie','csdn','github','hellogithub','jianshu','juejin','nodeseek','v2ex');
--   update sources set category='游戏娱乐' where src_id in ('acfun','bilibili','genshin','honkai','ithome-xijiayi','lol','miyoushe','starrail','weread','yystv');
--   update sources set category='社区' where src_id in ('douban-group','douban-movie','newsmth','ngabbs');
--   update sources set category='购物' where src_id in ('smzdm');

-- 热点（8）：热搜榜类
update sources set category = '热点' where src_id in
  ('baidu','weibo','zhihu','douyin','kuaishou','toutiao','tieba','zhihu-daily');

-- 新闻媒体（6）：门户/报纸
update sources set category = '新闻媒体' where src_id in
  ('qq-news','sina','sina-news','netease-news','thepaper','nytimes');

-- 科技（10）：科技媒体/数码
update sources set category = '科技' where src_id in
  ('36kr','ithome','huxiu','ifanr','geekpark','sspai','dgtle','guokr','hackernews','51cto');

-- 开发（8）：技术社区/开源
update sources set category = '开发' where src_id in
  ('github','hellogithub','juejin','csdn','v2ex','nodeseek','52pojie','jianshu');

-- 社区（4）：论坛
update sources set category = '社区' where src_id in
  ('hupu','ngabbs','newsmth','douban-group');

-- 游戏（7）
update sources set category = '游戏' where src_id in
  ('lol','genshin','honkai','starrail','miyoushe','yystv','ithome-xijiayi');

-- 娱乐（4）
update sources set category = '娱乐' where src_id in
  ('bilibili','acfun','douban-movie','weread');

-- 生活（2）：天气/历史小知识
update sources set category = '生活' where src_id in ('weatheralarm','history');

-- 购物（1）
update sources set category = '购物' where src_id in ('smzdm');

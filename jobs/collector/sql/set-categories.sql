-- 分类重排（2026-10-19，用户要求）：
--   ① 购物分类只有 1 个源（什么值得买）→ 并入「社区」
--   ② 财经原本只有 1 个（同花顺），而华尔街见闻/财联社/金十/雪球 被塞在「综合」→ 单拎成「财经」
--   结果：6 个分类 —— 综合 / 财经 / 科技 / 开发 / 社区 / 娱乐
BEGIN;
-- 财经（5 个）
UPDATE sources SET category='财经' WHERE engine='custom' AND src_id IN
  ('wallstreetcn','cls','jin10','tonghuashun','xueqiu');
-- 社区（并入什么值得买）
UPDATE sources SET category='社区' WHERE engine='custom' AND src_id IN
  ('hupu','tieba','douban-group','ngabbs','newsmth','52pojie','nodeseek','jianshu','smzdm');
-- 娱乐
UPDATE sources SET category='娱乐' WHERE engine='custom' AND src_id IN
  ('douyin','kuaishou','bilibili','douban','douban-movie','gcores','dongqiudi','steam',
   'acfun','yystv','lol','genshin','honkai','starrail','miyoushe','ithome-xijiayi');
-- 科技
UPDATE sources SET category='科技' WHERE engine='custom' AND src_id IN
  ('36kr','huxiu','ithome','ifanr','sspai','geekpark','dgtle','guokr','qbitai','solidot','freebuf');
-- 开发
UPDATE sources SET category='开发' WHERE engine='custom' AND src_id IN
  ('v2ex','cnblogs','nowcoder','github','juejin','csdn','oschina','51cto','hellogithub',
   'hackernews','producthunt');
-- 综合（平台 / 门户 / 新闻 / 工具）
UPDATE sources SET category='综合' WHERE engine='custom' AND src_id IN
  ('zhihu','weibo','baidu','toutiao','qq-news','netease-news','thepaper','ifeng','sina',
   'sina-news','cankaoxiaoxi','nytimes','weread','zhihu-daily','weatheralarm','history');
COMMIT;

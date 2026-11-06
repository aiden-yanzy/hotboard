-- 源默认排序（按权威性/内容质量分层）—— 全新部署的排序唯一来源
--
-- 为什么需要：sources.sort_order 为空时，api 按 `order by sort_order nulls last, name` 排序，
--   会把「今日头条热榜」之类排到第一位、把知乎挤到第 14 位，
--   前端数据源标签默认只显示前几个 → 用户看不到知乎等头部源。
--
-- 幂等：只 UPDATE 已存在的行，重复执行无副作用；不动 name/category。
-- 本文件由旧库权威排序导出（src_id → sort_order），新增源请追加一行。
BEGIN;
UPDATE sources SET sort_order=1 WHERE engine='custom' AND src_id='zhihu';
UPDATE sources SET sort_order=2 WHERE engine='custom' AND src_id='weibo';
UPDATE sources SET sort_order=3 WHERE engine='custom' AND src_id='baidu';
UPDATE sources SET sort_order=4 WHERE engine='custom' AND src_id='toutiao';
UPDATE sources SET sort_order=5 WHERE engine='custom' AND src_id='douyin';
UPDATE sources SET sort_order=6 WHERE engine='custom' AND src_id='kuaishou';
UPDATE sources SET sort_order=7 WHERE engine='custom' AND src_id='bilibili';
UPDATE sources SET sort_order=8 WHERE engine='custom' AND src_id='qq-news';
UPDATE sources SET sort_order=9 WHERE engine='custom' AND src_id='netease-news';
UPDATE sources SET sort_order=10 WHERE engine='custom' AND src_id='thepaper';
UPDATE sources SET sort_order=11 WHERE engine='custom' AND src_id='ifeng';
UPDATE sources SET sort_order=12 WHERE engine='custom' AND src_id='sina';
UPDATE sources SET sort_order=13 WHERE engine='custom' AND src_id='sina-news';
UPDATE sources SET sort_order=14 WHERE engine='custom' AND src_id='cankaoxiaoxi';
UPDATE sources SET sort_order=15 WHERE engine='custom' AND src_id='wallstreetcn';
UPDATE sources SET sort_order=16 WHERE engine='custom' AND src_id='cls';
UPDATE sources SET sort_order=17 WHERE engine='custom' AND src_id='jin10';
UPDATE sources SET sort_order=18 WHERE engine='custom' AND src_id='tonghuashun';
UPDATE sources SET sort_order=19 WHERE engine='custom' AND src_id='xueqiu';
UPDATE sources SET sort_order=20 WHERE engine='custom' AND src_id='36kr';
UPDATE sources SET sort_order=21 WHERE engine='custom' AND src_id='huxiu';
UPDATE sources SET sort_order=22 WHERE engine='custom' AND src_id='ithome';
UPDATE sources SET sort_order=23 WHERE engine='custom' AND src_id='ifanr';
UPDATE sources SET sort_order=24 WHERE engine='custom' AND src_id='sspai';
UPDATE sources SET sort_order=25 WHERE engine='custom' AND src_id='geekpark';
UPDATE sources SET sort_order=26 WHERE engine='custom' AND src_id='dgtle';
UPDATE sources SET sort_order=27 WHERE engine='custom' AND src_id='guokr';
UPDATE sources SET sort_order=28 WHERE engine='custom' AND src_id='qbitai';
UPDATE sources SET sort_order=29 WHERE engine='custom' AND src_id='solidot';
UPDATE sources SET sort_order=30 WHERE engine='custom' AND src_id='hupu';
UPDATE sources SET sort_order=31 WHERE engine='custom' AND src_id='tieba';
UPDATE sources SET sort_order=32 WHERE engine='custom' AND src_id='douban-group';
UPDATE sources SET sort_order=33 WHERE engine='custom' AND src_id='douban';
UPDATE sources SET sort_order=34 WHERE engine='custom' AND src_id='douban-movie';
UPDATE sources SET sort_order=35 WHERE engine='custom' AND src_id='v2ex';
UPDATE sources SET sort_order=36 WHERE engine='custom' AND src_id='ngabbs';
UPDATE sources SET sort_order=37 WHERE engine='custom' AND src_id='newsmth';
UPDATE sources SET sort_order=38 WHERE engine='custom' AND src_id='52pojie';
UPDATE sources SET sort_order=39 WHERE engine='custom' AND src_id='nodeseek';
UPDATE sources SET sort_order=40 WHERE engine='custom' AND src_id='cnblogs';
UPDATE sources SET sort_order=41 WHERE engine='custom' AND src_id='nowcoder';
UPDATE sources SET sort_order=42 WHERE engine='custom' AND src_id='freebuf';
UPDATE sources SET sort_order=43 WHERE engine='custom' AND src_id='github';
UPDATE sources SET sort_order=44 WHERE engine='custom' AND src_id='juejin';
UPDATE sources SET sort_order=45 WHERE engine='custom' AND src_id='csdn';
UPDATE sources SET sort_order=46 WHERE engine='custom' AND src_id='oschina';
UPDATE sources SET sort_order=47 WHERE engine='custom' AND src_id='51cto';
UPDATE sources SET sort_order=48 WHERE engine='custom' AND src_id='jianshu';
UPDATE sources SET sort_order=49 WHERE engine='custom' AND src_id='hellogithub';
UPDATE sources SET sort_order=50 WHERE engine='custom' AND src_id='hackernews';
UPDATE sources SET sort_order=51 WHERE engine='custom' AND src_id='producthunt';
UPDATE sources SET sort_order=52 WHERE engine='custom' AND src_id='nytimes';
UPDATE sources SET sort_order=53 WHERE engine='custom' AND src_id='gcores';
UPDATE sources SET sort_order=54 WHERE engine='custom' AND src_id='dongqiudi';
UPDATE sources SET sort_order=55 WHERE engine='custom' AND src_id='steam';
UPDATE sources SET sort_order=56 WHERE engine='custom' AND src_id='acfun';
UPDATE sources SET sort_order=57 WHERE engine='custom' AND src_id='yystv';
UPDATE sources SET sort_order=58 WHERE engine='custom' AND src_id='lol';
UPDATE sources SET sort_order=59 WHERE engine='custom' AND src_id='genshin';
UPDATE sources SET sort_order=60 WHERE engine='custom' AND src_id='honkai';
UPDATE sources SET sort_order=61 WHERE engine='custom' AND src_id='starrail';
UPDATE sources SET sort_order=62 WHERE engine='custom' AND src_id='miyoushe';
UPDATE sources SET sort_order=63 WHERE engine='custom' AND src_id='smzdm';
UPDATE sources SET sort_order=64 WHERE engine='custom' AND src_id='weread';
UPDATE sources SET sort_order=65 WHERE engine='custom' AND src_id='zhihu-daily';
UPDATE sources SET sort_order=66 WHERE engine='custom' AND src_id='ithome-xijiayi';
UPDATE sources SET sort_order=67 WHERE engine='custom' AND src_id='weatheralarm';
UPDATE sources SET sort_order=68 WHERE engine='custom' AND src_id='history';
COMMIT;

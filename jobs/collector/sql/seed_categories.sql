-- 分类种子：让**全新库**（云端一键部署）也有正确的分类，幂等、可重复执行
--
-- ⚠️ 2026-11-06 修正两处：
--   ① 原来按 `name` 匹配，但自研适配器（custom 引擎）的行 name 是中文展示名
--      （例：src_id='cls' / name='财联社电报'），拿英文 id 去匹配**一行都打不中**，
--      这份种子实际上形同虚设。改为按 `src_id` 匹配。
--   ② 缺少 '财经' 分类 → 财经下只剩适配器自带财经的那一个源（同花顺），
--      财联社/金十/华尔街见闻/雪球全被归到"综合"。
--
-- 权威来源是各适配器模块里的 CATEGORY（bootstrap 时写入）；
-- 这个文件用于「批量纠正已有库」，两边要一起改。
begin;

update sources set category = '财经' where engine = 'custom' and src_id in ('cls', 'jin10', 'wallstreetcn', 'xueqiu', 'tonghuashun', 'fastbull');
update sources set category = '娱乐' where engine = 'custom' and src_id in ('acfun', 'bilibili', 'dongqiudi', 'douban-movie', 'genshin', 'honkai', 'ithome-xijiayi', 'lol', 'miyoushe', 'starrail', 'weread', 'yystv', 'douyin', 'kuaishou', 'gcores', 'steam');
update sources set category = '开发' where engine = 'custom' and src_id in ('51cto', '52pojie', 'cnblogs', 'csdn', 'freebuf', 'github', 'hellogithub', 'jianshu', 'juejin', 'nodeseek', 'nowcoder', 'oschina', 'producthunt', 'v2ex');
update sources set category = '社区' where engine = 'custom' and src_id in ('douban', 'douban-group', 'history', 'hupu', 'newsmth', 'ngabbs', 'tieba', 'weatheralarm');
update sources set category = '科技' where engine = 'custom' and src_id in ('36kr', 'dgtle', 'geekpark', 'guokr', 'huxiu', 'ifanr', 'ithome', 'qbitai', 'solidot', 'sspai', '_36kr', 'pcbeta');
update sources set category = '购物' where engine = 'custom' and src_id in ('smzdm', 'steammkt');
-- 综合：其余默认（bootstrap 已按适配器写好），这里兜底把空分类的补成综合
update sources set category = '综合' where engine = 'custom' and category is null;

commit;

-- 校验：select category, count(*) from sources where engine='custom' and enabled group by 1 order by 2 desc;

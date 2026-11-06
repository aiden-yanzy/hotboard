-- 2026-10-12 分类重划（第二版）
-- 原则：① **单一维度** —— 只按"内容主题领域"分（旧方案把"来源形态"和"领域"混在一层：
--          新闻媒体/社区/购物 是形态，科技/游戏/娱乐 是领域）
--       ② **互斥** —— 一个源只归一类
--       ③ **不设孤儿分类** —— 只有 1 个源的分类不做独立分类（旧「购物」3 个源并入生活购物）
--       ④ **命名统一为领域名**，一眼能看出里面是什么：
--          热点→综合热搜、新闻媒体→新闻资讯、科技→科技数码、开发→编程开发、
--          娱乐→影音娱乐、社区→社区论坛、游戏→游戏动漫
--       ⑤ 跨领域的**热搜榜**（微博/知乎/百度/抖音/头条/快手/贴吧）单列「综合热搜」，不硬塞进某个领域
-- 新增（目前仅 newsnow 侧有源，引擎暂停中，启用即生效）：财经、体育
--
-- 回滚：dailyhot 侧的旧映射见 sql/recategorize_20261010.sql（热点/新闻媒体/科技/开发/社区/游戏/娱乐/生活/购物）

begin;

-- ===== dailyhot（当前唯一在跑、前端可见的 50 个源）=====
update sources set category = '综合热搜'
 where engine = 'dailyhot'
   and name in ('baidu','douyin','kuaishou','tieba','toutiao','weibo','zhihu','zhihu-daily');

update sources set category = '新闻资讯'
 where engine = 'dailyhot'
   and name in ('netease-news','nytimes','qq-news','sina','sina-news','thepaper');

update sources set category = '科技数码'
 where engine = 'dailyhot'
   and name in ('36kr','dgtle','geekpark','guokr','huxiu','ifanr','ithome','sspai');

update sources set category = '编程开发'
 where engine = 'dailyhot'
   and name in ('52pojie','csdn','github','hellogithub','jianshu','juejin','nodeseek','v2ex','51cto','hackernews');

update sources set category = '游戏动漫'
 where engine = 'dailyhot'
   and name in ('genshin','honkai','ithome-xijiayi','lol','miyoushe','starrail','yystv');

update sources set category = '影音娱乐'
 where engine = 'dailyhot'
   and name in ('acfun','bilibili','douban-movie','weread');

update sources set category = '社区论坛'
 where engine = 'dailyhot'
   and name in ('douban-group','hupu','newsmth','ngabbs');

update sources set category = '生活购物'
 where engine = 'dailyhot'
   and name in ('smzdm','history','weatheralarm');

-- ===== newsnow（引擎已暂停，同口径归类，将来启用即用）=====
update sources set category = '综合热搜'
 where engine = 'newsnow' and name in ('baidu','douyin','kuaishou','tieba','toutiao','weibo','zhihu');

update sources set category = '新闻资讯'
 where engine = 'newsnow' and name in ('cankaoxiaoxi','ifeng','zaobao','thepaper');

update sources set category = '财经'
 where engine = 'newsnow' and name in ('fastbull','jin10','wallstreetcn','xueqiu');

update sources set category = '科技数码'
 where engine = 'newsnow' and name in ('_36kr','ithome','solidot','sspai');

update sources set category = '编程开发'
 where engine = 'newsnow' and name in ('freebuf','juejin','nowcoder','pcbeta','v2ex');

update sources set category = '影音娱乐'
 where engine = 'newsnow' and name in ('bilibili');

update sources set category = '体育'
 where engine = 'newsnow' and name in ('dongqiudi');

update sources set category = '社区论坛'
 where engine = 'newsnow' and name in ('douban','hupu');

update sources set category = '生活购物'
 where engine = 'newsnow' and name in ('smzdm','steammkt');

commit;

-- 校验（dailyhot 应为 8 类 / 50 源）
select category,
       count(*) filter (where engine = 'dailyhot') as dailyhot,
       count(*) filter (where engine = 'newsnow')  as newsnow
from sources group by 1 order by 2 desc, 1;

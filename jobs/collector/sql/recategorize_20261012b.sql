-- 2026-10-12 分类重划（第三版，用户指定）：收敛到**六个两字分类**
--   综合（综合热搜 + 新闻资讯）、科技（科技数码）、娱乐（游戏动漫 + 影音娱乐）、
--   开发（编程开发）、社区（社区论坛 + 生活）、购物
-- 同时移除前端「全部」分类（前端改动，见 store/CategoryBar）
-- 回滚：第二版映射见 sql/recategorize_20261012.sql

begin;

-- 综合 = 综合热搜 + 新闻资讯（+ 仅 newsnow 有的财经，也算新闻）
update sources set category = '综合'
 where category in ('综合热搜', '新闻资讯', '财经');

update sources set category = '科技' where category = '科技数码';

-- 娱乐 = 游戏动漫 + 影音娱乐（+ 仅 newsnow 有的体育，并入娱乐）
update sources set category = '娱乐'
 where category in ('游戏动漫', '影音娱乐', '体育');

update sources set category = '开发' where category = '编程开发';

-- 社区 = 社区论坛 + 生活（气象台 / 历史上的今天属于生活服务，跟社区同层）
update sources set category = '社区'
 where category in ('社区论坛', '生活')
    or (category = '生活购物' and name in ('weatheralarm', 'history'));

-- 购物 = 电商导购（生活购物里剩下的）
update sources set category = '购物'
 where category = '购物'
    or (category = '生活购物');

commit;

-- 校验（dailyhot 应为 6 类 / 50 源）
select category,
       count(*) filter (where engine = 'dailyhot') as dailyhot,
       count(*) filter (where engine = 'newsnow')  as newsnow
from sources group by 1 order by 2 desc, 1;

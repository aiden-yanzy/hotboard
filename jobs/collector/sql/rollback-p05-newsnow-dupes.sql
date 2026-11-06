-- P0.5 回滚：把 newsnow 侧重叠源重新启用（2026-10-19 生成）
-- 事故/变更记录见 docs/抓取逻辑规范化-设计与迁移计划.md
update sources set enabled=true where id='newsnow:36kr';  -- 36kr
update sources set enabled=true where id='newsnow:baidu';  -- baidu
update sources set enabled=true where id='newsnow:bilibili';  -- bilibili
update sources set enabled=true where id='newsnow:douyin';  -- douyin
update sources set enabled=true where id='newsnow:hackernews';  -- hackernews
update sources set enabled=true where id='newsnow:hupu';  -- hupu
update sources set enabled=true where id='newsnow:ithome';  -- ithome
update sources set enabled=true where id='newsnow:juejin';  -- juejin
update sources set enabled=true where id='newsnow:kuaishou';  -- kuaishou
update sources set enabled=true where id='newsnow:sspai';  -- sspai
update sources set enabled=true where id='newsnow:thepaper';  -- thepaper
update sources set enabled=true where id='newsnow:tieba';  -- tieba
update sources set enabled=true where id='newsnow:toutiao';  -- toutiao
update sources set enabled=true where id='newsnow:v2ex';  -- v2ex
update sources set enabled=true where id='newsnow:weibo';  -- weibo
update sources set enabled=true where id='newsnow:zhihu';  -- zhihu

-- P2 前置：newsnow 剩余 2 源（zaobao/fastbull）重新启用（2026-10-19 生成）
-- 背景：用户不要这两个源了；newsnow 引擎随之下线
update sources set enabled=true where id='newsnow:fastbull';  -- fastbull
update sources set enabled=true where id='newsnow:zaobao';  -- zaobao

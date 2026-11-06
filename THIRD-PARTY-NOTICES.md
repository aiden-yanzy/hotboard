# 第三方声明 / Third-Party Notices

本项目在开发过程中参考、移植或复用了以下开源项目。按照各自许可证要求，在此保留版权声明。

---

## DailyHot / DailyHotApi

- **用途**：`apps/engine` 派生自 DailyHotApi；`jobs/collector/adapters/` 下大部分源适配器由 DailyHotApi 的 TypeScript 实现改写为 Python。
- **许可证**：MIT
- **仓库**：
  - https://github.com/imsyy/DailyHot
  - https://github.com/imsyy/DailyHotApi

```
MIT License

Copyright (c) 2023 imsyy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## newsnow

- **用途**：曾作为第二数据源引擎接入（`apps/engine` 的互补源），部分源的抓取思路参考其实现。
- **许可证**：MIT
- **仓库**：https://github.com/ourongxing/newsnow

```
MIT License

Copyright (c) 2023 ourongxing

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 图标

- **Lucide Icons**（ISKCON License / MIT）—— 顶栏刷新、主题切换、设置、返回顶部等图标路径
  https://lucide.dev
- 各数据源站点的 favicon / logo 版权归各自站点所有，本项目仅作识别用途缓存展示。

---

## 其他依赖

各子项目的 `package.json` / `requirements.txt` 中列出的依赖均遵循其各自许可证，详见对应依赖仓库。

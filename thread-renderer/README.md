# adnmb-quests-tools/thread-render

依照 `divisions.yaml` 中的结构将下载的串渲染为 Markdown 文档。

## `divisions.yaml`

格式可参考[这里](https://github.com/FToovvr/adnmb-quests-archive/blob/quests/fxc/%E5%AE%89%E9%A1%BA%E5%B1%B1%E5%BA%84/divisions.yaml)。

## 代码结构

* `src`
    * `configloader` 将 `divisions.yaml` 转化为基于 `DivisionRule` 的结构。
        匹配规则等会被解析，但不会被填充/展开。
    * `divisiontree` 依据 `DivisionRule` 建立 以 `DivisionTreeNode` 为根结点的树。
        串内文本会被载入，然后会再展开收集类的匹配规则。
    * `generating` 将 `DivisionTreeNode` 为根结点的树渲染为 Markdown 格式的文档。
        生成文档只要求能同时在 GitHub 上正确预览且能在 Jekyll 上正确渲染，不要求直接查看的可读性。
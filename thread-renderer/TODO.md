# TODO

## make-book-from-dump

### 下个commit前

### 优先

* [ ] `post-rules[].description`
* [ ] 在叶段落标题后添加「返回最顶部」按钮
* [ ] 支持多行`text-until`
* [ ] 支持为附加内容分段落、起名
* [ ] 支持配置是否不增加附加内容的嵌套层级
* [ ] `show-attachment: top | bottom`
* [ ] 生成frontmatter

### 一般重要

* [ ] 为`divisions.yaml`的使用方式编写说明文档
* [ ] 补齐脚本的注释与文档
* [ ] 支持生成纯markdown文件
* [ ] 输出友善的错误信息
* [ ] 如果`divisions.yaml`没有变化，则根据po是否有新回复来判断是否需要更新

### 不重要

* [ ] 为被切割的串提供更多上下文，如一共切割了多少部分，当前是第几部分
* [ ] 在没有指定日志配置文件时，调低日志等级阈值到INFO
* [ ] 细化对引用链接展开的控制，如支持生成内容折叠的details标签
  * [ ] `expand-quote-links: true | false`改为`quote-link-rules: open | close | plain | { … }`

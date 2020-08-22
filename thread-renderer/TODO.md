# TODO

## make-book-from-dump

### 下个commit前

### 优先

* [ ] 细化对引用链接展开的控制，如支持生成内容折叠的details标签
* [ ] 各文件中的目录列表
* [ ] `post-rules[].description`
* [ ] 允许对带有图片的被切割的串指定图片所处的部分
* [ ] `expand-quote-links: true | false`改为`quote-link-rules: open | close | plain | { … }`

### 一般重要

* [ ] 为`divisions.yaml`的使用方式编写说明文档
* [ ] 补齐脚本的注释与文档
* [ ] 支持生成纯markdown文件

### 不重要

* [ ] 为被切割的串提供更多上下文，如一共切割了多少部分，当前是第几部分
* [ ] 在没有指定日志配置文件时，调低日志等级阈值到INFO
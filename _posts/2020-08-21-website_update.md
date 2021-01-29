---
layout: post
redirect_from: /2020/08/21/website_update/
title: "更新 CodingTour"
date: 2020-08-21 23:32:20 +0800
categories: [前端]
article_type: 1
typora-root-url: ../../github.io
---

最近对个人网站做了一次更新，主要做了这么几件事：

1. 优化 CSS：
2. 支持 Dark Mode
3. 新的 Logo


# 优化 CSS

现在的这套 CSS 代码自去年建站以来就没怎么动过，文件既没有压缩，还充斥着各种尝试、注释和临时的解决方案。这次想通过对一些工具的使用来指导自己改善代码，我选择了两个工具：

1. Chrome Lighthouse - 对网站生成性能、SEO 等报告指导优化方向
2. Chrome Coverage - 适用于人工剪枝

分析后决定：

- 源文件压缩生成 min 文件，减少传输量
- 对不使用和不常使用的样式进行调整删除
- 引入 SASS，将全局关键配置做成常量

由于网站是基于 Jekyll 搭建的，通过简单配置就能实现对 SASS 语法的支持和压缩：

```yaml
sass:
    sass_dir: ./css
    style: compressed
```

同时考虑兼容性的问题，采用的是 SCSS 写法。

Coverage 就是体力活了。

经过一系列的优化，Coverage 达到了 90%，主样式文件从 16.5 kB 降到了 5.6 kB，整体性能得到了较大的改善：

![](/assets/img/image-20200824004312465.png)

# 支持 Dark Mode

在开始之前我特意找了几篇实践文章和应用以获取灵感，其中 [A Complete Guide to Dark Mode on the Web](https://css-tricks.com/a-complete-guide-to-dark-mode-on-the-web/) 这篇文章细节很丰富，对我帮助很大；Chrome 的  [Stylus](https://github.com/StylishThemes/GitHub-Dark) 也给我提供了很好的配色作为参考。

然而我还是低估了 Dark Mode 的适配难度，我几乎所有的 CSS 文件里的样式都要进行适配，这是一个工作量很大的体力活，究其原因还是因为初版做的太糙。

## 动态更新配色

我选择了纯 CSS 的方案，在该方案下，网站跟随用户系统的偏好来决定是否启用 Dark Mode，好处是页面不用重新刷新，对用户来说完全是透明的。

只需要预先定义好两个常量值：

```scss
// Light Mode
$headerColor: #515151;

// Dark Mode
$baseColorDark: #c6c6c6;
```

创建一个 `:root` 伪元素：

```scss
:root {
  --base-color: #{$baseColor};
}
```

然后根据 `@media` 更新 Dark Mode 下的伪元素：

```scss
@media (prefers-color-scheme: dark) {
  :root {
    --base-color: #{$baseColorDark};
  }
}
```

最后在需要用到这个配置地方只需要：

```scss
.title {
  color: var(--base-color);
}
```

一般来说接入 Dark Mode 后应用的配色都会进行一轮调整，减少色值的使用，多数情况下选择黑白色作为主题色是简单又普适的方案。

## 布局调整

我为了日后维护方便减化了一些效果，对一些布局也进行了调整，让整体结构变得更简单，同时将布局单位进行了统一，以 `rem`、`em` 为主，这个阶段也是体力活，根据实际情况来调整。

以 TOC 为例，我选择了扁平化的设计，不再做展开、折叠的效果，并限制最多显示两层，减少了对用户的干扰。由于我使用了开源的 `Tocbot` 来实现 TOC，它有诸多不足：

- 不支持层级的最大深度配置
- 样式配置过于死板
- 最新版本只有压缩后的 min 文件源码，调试、修改不方便

我希望最多显示两层，理论上我只需要定义两个样式，但实际上我要定义从 H1 到 H5 全部的样式，因为我并不能保证我的内容中只使用特定的标签。如果能忽略我的实际标签，只固定使用 H1 和 H2 的样式就好了，为此我写了一个过滤函数：

```javascript
headingObjectCallback: (n, t) => {
  if (initialLevel == null || n.headingLevel == initialLevel) {
    previousLevel = null;
    initialLevel = n.headingLevel;
    n.headingLevel = 1;
    n.nodeName = "H1";
    return n;
  }

  if (previousLevel == null || previousLevel == n.headingLevel) {
    previousLevel = n.headingLevel;
    n.headingLevel = 2;
    n.nodeName = "H2";
    return n;
  }
  return;
}
```

除此之外对 min 文件的源码做了几处兼容实现了我想要的效果。

经过这次对 `Tocbot` 的改造，我重新思考了一个 TOC 控件应该如何简单、优雅的实现：

1. 用 querySelector 找出所有的 H 元素，得到一个元素数组
2. 对数组进行过滤后，生成一个 ul/ol 树
3. 使用 CSS 润色即可

其实挺简单的。

# 新的 Logo

简单设计了几种样式：

![](/assets/img/image-20200823193517903.png)

实际对比后还是元素简单、辨识度高的效果最好。

# 最后

优化的过程充满乐趣和挑战，有些细节就留在下次再处理了，如 Safari 的顶部适配：

![](/assets/img/image-20200824004312466.png)

遗留问题汇总：

- 封面图
- 导航栏按钮事件触发范围调整
- 考虑顶部浮动窗口存在的必要性
- 代码高亮
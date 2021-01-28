---
layout: post
title: "博客性能优化"
date: 2021-01-28 12:33:51 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

上次将博客托管到 Vercel 之后访问速度有了很大改善，于是就想深入做一些优化，这是本次优化过后 LightHouse 的评分：

![](/assets/img/blog_performance-2.jpg)

除了性能改善，还修复了所有的 Accessibility 问题，我希望能最终构建出一个美观、简单、对 SEO 友好且快速的博客，下面就来说说本次优化的具体内容。

# 字体瘦身

图标库采用了 [FontAwesome 5](https://fontawesome.com)，完整的 FontAwesome 尺寸很大：

| 文件 | 大小 |
| ------------------- | ------ |
| fontawesome.min.css | 12.3kB |
| fa-solid-900.woff2  | 75.7kB |
| fa-brands-400.woff2 | 74.8kB |
| brands.min.css | 732B |
| solid.min.css | 741B |

而这个博客只使用了其中10个图标：

| <i class="icon-heart"></i>    | <i class="icon-envelope"></i>        | <i class="icon-bars"></i>             | <i class="icon-circle"></i> | <i class="icon-battery"></i>        |
| ----------------------------- | ------------------------------------ | ------------------------------------- | --------------------------- | ----------------------------------- |
| <i class="icon-arrow-up"></i> | <i class="icon-long-arrow-left"></i> | <i class="icon-long-arrow-right"></i> | <i class="icon-github"></i> | <i class="icon-stack-overflow"></i> |

所以这个环节的思路就是剔除冗余，在具体的行动项上有两种做法：

1. 困难模式 - 本地对字体资源进行裁剪
2. 简单模式 - 使用生成器

## 困难模式

先将字体和样式文件存储到本地，删除不需要的文件，剔除多余的样式，最后用字体修改软件编辑字体文件：

![](/assets/img/blog_performance-1.jpg)

这种方式维护性很差，pass。

## 简单模式

找一个在线的字体生成工具，按需生成 ttf、svg 等文件，比较流行的平台有这些：

- [IcoMoon](https://icomoon.io/)
- [Fontello](https://fontello.com/)
- [Fontastic](http://fontastic.me/)
- [iconfont](https://www.iconfont.cn/)

经过一番对决，最终我选择了 IcoMoon，它有如下优势：

- 配置项丰富 - 可以在线设置 Baseline、浏览器兼容性、编辑字形等
- 图标库丰富 - 可以在指定的图库里搜索（iconfont 的硬伤，如果能完善一下还是很好用的）
- 使用方便

单纯从文件大小角度来看，iconfont 还要更小一点（差距在10%以内），要用起来的话得调整两处样式：

```css
@font-face {font-family: "iconfont";
  src: url('iconfont.eot?t=1611741050729'); /* IE9 */
  src: url('iconfont.eot?t=1611741050729#iefix') format('embedded-opentype'), /* IE6-IE8 */
  url('data:application/x-font-woff2;charset=utf-8;base64,d09...') format('woff2'),
  url('iconfont.woff?t=1611741050729') format('woff'),
  url('iconfont.ttf?t=1611741050729') format('truetype'), /* chrome, firefox, opera, Safari, Android, iOS 4.2+ */
  url('iconfont.svg?t=1611741050729#iconfont') format('svg'); /* iOS 4.1- */
}
...
```

eot、woff2 可以移除（放弃 IE）。

此外可以将 `.iconfont` 的样式：

```css
.iconfont {
  font-family: "iconfont" !important;
  font-size: 16px;
  font-style: normal;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

替换为：

```css
[class^="icon-"], [class*=" icon-"] {
  font-family: 'iconfont' !important;
  font-size: 16px;
  font-style: normal;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
```

这样在使用时可以直接用 `icon-xxx` 而不是 `iconfont icon-xxx`。

相比之下 IcoMoon 就省心多了，这些事它会自己搞定。

> 注意：FontAwesome 的图标默认是「居中」+「Fit to Canvas」的，无论选择哪个平台，记得检查下是否一致。

裁剪前后对比：

| 文件                | 大小   | 裁剪后 |
| ------------------- | ------ | ------ |
| fontawesome.min.css | 12.3kB | 1.1kB  |
| fa-solid-900.woff2  | 75.7kB | 3.1kB  |
| fa-brands-400.woff2 | 74.8kB | -      |
| brands.min.css | 732B | -      |
| solid.min.css | 741B | -      |

从 164kB 减少到了 4.2kB，优化幅度达 **97%**。

# 图片压缩

原先使用的图片都有经过 [ImageOptim](https://imageoptim.com/mac) 无损压缩，效果比较有限，这次直接用了有损压缩：

| 项目 | 原始 | 无损压缩 | 有损压缩 |
| ---- | ----- | ----- | ---- |
| 图片集 | 10.8M | 9.8M | 4.9M |

ImageOptim 会为图片自动选择合适的压缩算法，很省心。

此外将 [Gravatar](https://www.gravatar.com/) 的头像从 350x350 降低到了 200x200：

| 头像尺寸 | 大小   |
| -------- | ------ |
| 350*350  | 27.4kB |
| 200*200  | 11.8kB |

大约可以节省 **15.6kB**。

# 功能降级

在不影响主要功能的情况移除了部分依赖：

| 文件                                     | 大小   | 说明               |
| ---------------------------------------- | ------ | ------------------ |
| jquery-3.2.1.min.js                      | 32.5kB | 仅被 fancybox 依赖 |
| jquery.fancybox.min.js                   | 22.6kB | 图片浏览插件       |
| jquery.fancybox.min.css                  | 3.7kB  | 图片浏览插件       |
| mem8YaGs126MiZpBA-UFVZ0bf8pkAg.woff2     | 9.2kB  | Open Sans          |
| mem5YaGs126MiZpBA-UN7rgOUuhpKKSTjw.woff2 | 9.1kB  | Open Sans          |
| busuanzi.pure.mini.js                    | 2.1kB  | PV 统计            |

简单说下移除的逻辑：

- [busuanzi](https://busuanzi.ibruce.info/) - 是用来统计阅读量的，实际意义不大
- [fancybox](https://fancyapps.com/) - 图片浏览插件，效果很棒，但作为唯一对 jQuery 有依赖的插件，考虑到 jQuery 自身的尺寸挺大的，就一并移除了，后续可能会考虑对 jQuery 无依赖的其他插件
- [Open Sans](https://fonts.google.com/specimen/Open+Sans) - 是一款开源、免费的字体，整体素质很高，也是使用最多的 Web 字体之一，因为应用广泛，意味着在大多数情况下它可能已经在用户的缓存里了，虽然有如上优点，但对我的吸引力不足，所以就移除了（ps: 可能对低版本的移动设备来说体验会比较好）

这一部分可以使网络数据量减少 **79.2kB**。

# 图片懒加载

原先想通过浏览器原生的 `loading="lazy"` 来实现该功能，但测试后发现 *Chrome 87*、*Safari iOS 14* 没有默认开启该功能，而且行为也有差异：

> ...
>
> It turns out **Chrome is more impatient** than Firefox when loading images tagged as lazy. That means it loads the images much earlier, so an image will not be loaded when it appears at the screen but earlier than that. Firefox, on the other side, is loading the images almost when they are about to be shown at the screen.
>
> ...
>
> 
>
> 引用自 Stack Overflow: [Native lazy-loading (loading=lazy) not working even with flags enabled](https://stackoverflow.com/questions/57753240/native-lazy-loading-loading-lazy-not-working-even-with-flags-enabled)。

既然如此，那就用 `data-src` 结合 JS 的方式来实现。

第一个问题是如何输出带 `data-src` 的标签？如果直接写肯定不行，我还要在 Typora 里预览图片，用 Plugin 或 Hook 似乎可以，但 GitHub Pages 不支持自定义插件，我还想兼容现有的流程。

在读 [Rendering Process](https://jekyllrb.com/docs/rendering-process/) 文档的时候突然发现，原生的 [Liquid](https://shopify.github.io/liquid/) 就可以完美解决这个问题：

{% raw %}

```
{% if content contains '<img src=' %}
  {%- comment -%} 将 src 替换为 data-src {%- endcomment -%}
{% else %}
  {{ content }}
{% endif %}
```

{% endraw %}

设置 `data-src` 后需要给一个默认占位图，一般是用 1px 的透明图：

```
data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7
```

> ps: 来自 [Base64 Encode of 1x1px Transparent GIF](https://css-tricks.com/snippets/html/base64-encode-of-1x1px-transparent-gif/)。
>
> ps2: 去掉图片标签中的 `alt` 才能达到最佳效果。

三方库的选择上，对比了 [Lozad.js](https://github.com/ApoorvSaxena/lozad.js) 和 [vanilla-lazyload](https://github.com/verlok/vanilla-lazyload)，最终选择了 Lozad.js：

- 尺寸更小
- 使用起来更加简单

最终完整版：

{% raw %}

```
{%- comment -%} 图片懒加载 {%- endcomment -%}
{%- capture img_placehodler -%}
  data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7
{% endcapture%}

{% if content contains '<img src=' %}
  {% assign replacement = '<img src="' | append: img_placehodler | append: '" data-src=' %}
  {{ content | replace: '<img src=', replacement }}
  {% include lozad.html %}
{% else %}
  {{ content }}
{% endif %}
```

将 `{% include lozad.html %}` 放到条件判断里可以顺手解决按需加载的问题。

{% endraw %}

# 评论优化

## utterances

现在使用的 [Gitalk](https://gitalk.github.io/) 功能很完善，还有 loading 的 UI，但也架不住大：

| 文件                   | 大小   |
| ---------------------- | ------ |
| gitalk.css             | 20.5kB |
| gitalk.min.js          | 153kB  |
| 总计          | **173.5kB** |

相比之下 [utterances](https://utteranc.es/) 就很轻量了：

| 文件                   | 大小   |
| ---------------------- | ------ |
| utteranc.es/client.js  | 2.2kB  |
| utterances.html        | 1.2kB  |
| utterances.2a0774da.js | 10.8kB |
| utterances.css         | 8.1kB  |
| 总计          | **22.3kB** |

直接减少了 **87%**。

utterances 还有一个优势：Gitalk 需要 admin 用户访问对应的页面才能创建 issue，否则用户不能发表评论，而 utterances 是在第一个用户发表评论时创建 issue，无论当前用户是否是 admin，这点很实用。

## 自定义 loading

但 utterances 没有了 loading 还是有点遗憾，让我们完善它。

引入一个 spinner：

<i class="icon-spinner"></i>

实现纯 CSS 的 loading：

```css
<style>
    #comments-container { 
        text-align: center; 
        position: relative; 
        min-height: 6em;
    }
    #comments-container .loading {
        font-size: 2em;
        display: inline-block;
        position: absolute;
        top: 2em;
        z-index: -1;
        -webkit-animation:spin 1s linear infinite;
        -moz-animation:spin 1s linear infinite;
        animation:spin 1s infinite;
    }
  
    @-moz-keyframes spin { 100% { -moz-transform: rotate(360deg); } }
    @-webkit-keyframes spin { 100% { -webkit-transform: rotate(360deg); } }
    @keyframes spin { 100% { -webkit-transform: rotate(360deg); transform:rotate(360deg); } }

    .utterances { 
        max-width: 100%; 
        position: relative;
    }
    .utterances-frame {
        position: absolute;
    }
</style>
```

这里有一个 trick：当 utterances 加载完后需要隐藏 loading，看起来免不了要用 JS 监听+修改 DOM，这无疑又会带来一些维护成本，所以我将 loading 调整为绝对布局，下探 2em，这样当 utterances 加载完后会自然顶上去盖住 loading，避免了引入额外脚本的工作。

> ps: 滚动到博客底部查看该效果

## Dark Mode

utterances 支持 Dark 模式，但需要通过修改 script attribute 来实现，我用了一个简化的方案：

```css
@media (prefers-color-scheme: dark) {
  .main-content img, #comments-container { 
    -webkit-filter: brightness(0.8);
    filter: brightness(0.8);
  }
}
```

## 延迟请求

utterances 虽然尺寸不大，但如果用户滑不到底部也看不到，监听 `scroll` 事件可以找到一个相对完美的加载时机：

{% raw %}

```javascript
<script>
    function renderCommentsContainer() {
        var container = document.getElementById('comments-container');

        var script = document.createElement('script');
        script.src = "https://utteranc.es/client.js";
        script.type = 'text/javascript';
        script.crossorigin = 'anonymous';
        script.setAttribute("async", "");
        script.setAttribute("issue-term", "title");
        script.setAttribute("repo", "{{ site.repository }}");
        script.setAttribute("label", "utteranc");
        script.setAttribute("theme", "github-light");

        container.append(script);
    }

    function onScroll() {
        const container = document.getElementById("comments-container");
        if (window.scrollY + window.innerHeight >= container.offsetTop) {
            window.removeEventListener('scroll', onScroll);
            renderCommentsContainer();
        }
    }

    window.addEventListener('scroll', onScroll, {passive: true});
</script> 
```

{% endraw %}

这样就能仅在用户滑动到评论区域的时候才加载相关资源。

# 按需加载

在之前的版本里，有些页面比较简单，比如它没有代码，但是仍然要不厌其烦的去加载 CSS 或 JS 等文件，对优化加载时间来说，每个 kB 都很重要，所以这一步的关键就是**只加载必要的依赖**。

经过分析有以下三种类型的资源可以加上条件依赖：

- 数学符号 - 如 $$n^{2}$$
- 代码高亮
- TOC

要实现上述目标有两个思路：

- 在 Front Matter 里定义文章的元数据，比如是否包含代码等 - **维护性差**
- 在编译期动态检查 - **最优解**

参考图片懒加载的方式可以实现最优解。

## 检查数学符号

{% raw %}

```
{%- comment -%} MathJax {%- endcomment -%}
{% if content contains 'math/tex' %}
  <script type="text/javascript" defer src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML"></script>
{% endif %}
```

{% endraw %}

涉及网络传输的文件：

| 文件                      | 大小   |
| ------------------------- | ------ |
| MathJax.js                | 17.4kB |
| TeX-MML-AM_CHTML.js       | 66.9kB |
| jax.js                    | 17.2kB |
| fontdata.js               | 10.3kB |
| MathJax_Math-Italic.woff  | 19.6kB |
| MathJax_Main-Regular.woff | 34.5kB |

可以减少 **166kB** 的网络传输量。

## 检查代码

{% raw %}

```
{%- comment -%} 语法高亮 {%- endcomment -%}
{% if content contains '<code>' %}
  <link rel="stylesheet" href="{{ '/assets/css/syntax.css?v=' | append: site.github.build_revision | relative_url }}" />
{% endif %}
```

{% endraw %}

只涉及一个代码高亮的样式文件，数据量是 **2.3kB**。

## 检查 TOC

{% raw %}

```
{%- comment -%} Table of Contents {%- endcomment -%}
{% assign has_toc = false %}
{% for item in page.toc_tags %}
  {% assign test = '</' | append: item | append: '>' %}
  {% if content contains test %}
    {% assign has_toc = true %}
    {% break %}
  {% endif %}
{% endfor %}
{% if has_toc %}
  {% include toc.html %}
{% endif %}
```

{% endraw %}

TOC 涉及两个文件：

| 文件          | 大小   |
| ------------- | ------ |
| tocbot.css    | 1.9kB  |
| tocbot.min.js | 11.8kB |

数据量是 **13.7kB**。

像 [建立可评估工作流](https://www.codingtour.com/posts/evaluable-workflow/) 这篇文章，由于不包含上述三项，可以减少 **182kB** 的网络传输量。

# 修复 Web Accessibility 问题

虽然和性能无关，但身为一个有理想主义的开发者，我还是希望花一点点时间去改善 [Accessibility](https://developer.mozilla.org/en-US/docs/Learn/Accessibility/What_is_accessibility) 问题。

幸运的是，Google Chrome Dev Tools 只检查出了两处问题。

## Form elements do not have associated labels

这个问题发生在右上角的 sidebar 切换功能上，我使用了一个 `checkbox` 来记录状态，根据[文档](https://web.dev/label/?utm_source=lighthouse&utm_medium=devtools)的说法，由于 `checkbox` 是表单元素，所以希望增加一个 `label` 提高它的阅读性。

由于我的 `checkbox` 只是用来记录状态，并不对用户可见，所以用 `display: none` 代替 `opacity: 0` 就能解决，这样也避免了添加完 `label` 后布局发生变化或者还要额外设置 `width`、`height` 或可见性等麻烦事。

## Background and foreground colors do not have a sufficient contrast ratio

这个问题发生在分页按钮上，根据[文档](https://web.dev/color-contrast/?utm_source=lighthouse&utm_medium=devtools)的说法，前景色和背景色要有一定的对比度，我的按钮需要达到 *4.5:1* 才行，不知道是不是因为我用了 SCSS 变量的原因，Google Chrome Dev Tools 会显示 "No Contrast information available" ，为此我找了一个[在线工具](https://contrast-ratio.com/)辅助我解决该问题。

这两个解决后 Accessibility 就能达到 100 分了。

# 总结

优化说到底就是集中在**资源请求量**和**网络传输量**上，资源能移除就移除，不能移除就延迟加载，选三个场景做个效果对比：

- 首页
- 尝试 Vercel - 首屏有两张图
- 《演进式架构》书评

先看下请求量的对比：

![](/assets/img/blog_performance-3.jpg)

基本上是 50% 的优化，再看看网络传输量的对比：

![](/assets/img/blog_performance-4.jpg)

大幅减少了网络传输量。

有些细节没有太过多深入，我希望在未来我的博客能将**快速**发挥到极致，并且我会尽可能地继续研究，还有很多东西需要学习。

之后我打算尝试将 MaxCDN 作为备用 CDN 来测试服务器的响应时间，并决定是否采用它。
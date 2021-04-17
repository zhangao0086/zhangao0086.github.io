---
layout: post
title: "上线「站内搜索」"
date: 2021-04-17 22:30:38 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

这周为博客增加了「站内搜索」功能，算是解决了自己搜索不便的一大痛点。

最开始打算实现像 [vuepress2](https://vuepress2.netlify.app/) 那样看起来很酷的效果，它的服务提供商是 [algolia](https://www.algolia.com/)，虽然有免费的版本，但限制很多，需要自己生成索引文件、手动上传至 algolia 的服务器、有搜索限额，最重要的是整个过程不能完全自动化（除非花钱），只得放弃。

后来想到利用 Jekyll 的文件处理流程，其实可以很容易的实时生成索引文件，类似于这样：

{% raw %}

```json
[
  {% for post in site.posts %}
    {
      "title": "{{ post.title }}",
      ...
    }
  {% endfor %}
}
```

{% endraw %}

然后再找一个功能完备的 JS 搜索库就可以了。一番查找后找到了专门做 Jekyll 搜索的库：[Simple-Jekyll-Search](https://github.com/christian-fei/Simple-Jekyll-Search)，它的原理很简单，首先通过 XHR 加载索引文件：

```javascript
function load (location, callback) {
  const xhr = getXHR()
  xhr.open('GET', location, true)
  xhr.onreadystatechange = createStateChangeListener(xhr, callback)
  xhr.send()
}

function createStateChangeListener (xhr, callback) {
  return function () {
    if (xhr.readyState === 4 && xhr.status === 200) {
      try {
        callback(null, JSON.parse(xhr.responseText))
      } catch (err) {
        callback(err, null)
      }
    }
  }
}

function getXHR () {
  return window.XMLHttpRequest ? new window.XMLHttpRequest() : new ActiveXObject('Microsoft.XMLHTTP')
}
```

遍历列表并匹配对象的 key 值：

```javascript
function findMatches (data, crit, strategy, opt) {
  const matches = []
  for (let i = 0; i < data.length && matches.length < opt.limit; i++) {
    const match = findMatchesInObject(data[i], crit, strategy, opt)
    if (match) {
      matches.push(match)
    }
  }
  return matches
}

function findMatchesInObject (obj, crit, strategy, opt) {
  for (const key in obj) {
    if (!isExcluded(obj[key], opt.exclude) && strategy.matches(obj[key], crit)) {
      return obj
    }
  }
}
```

有两种搜索策略，[fuzzysearch](https://github.com/bevacqua/fuzzysearch) or literal：

```javascript
function LiteralSearchStrategy () {
  this.matches = function (str, crit) {
    if (!str) return false
    str = str.trim().toLowerCase()
    crit = crit.endsWith(' ') ? [crit.toLowerCase()] : crit.trim().toLowerCase().split(' ')

    return crit.filter(word => str.indexOf(word) >= 0).length === crit.length
  }
}
```

fuzzysearch 会快很多，原理没去细看。

完整的索引文件创建方法：

{% raw %}

```json
---
layout: compress
---

[
  {% for post in site.posts %}
    {% assign post_date = post.date | date: '%Y-%m-%d' %}
    {% if post_date < "2019-01-01" %}
      {% break %}
    {% endif %}
  {% if insert_comma %},{% endif %}
  {
    "title": "{{ post.title | escape }}",
    "url": "{{ site.baseurl }}{{ post.url }}",
    "categories": "{{ post.categories | join: ', '}}",
    "tags": "{{ post.tags | join: ', ' }}",
    "date": "{{ post_date }}",
    {% include no-linenos.html content=post.content %}
    "snippet": "{{ content | strip_html | strip_newlines | remove_chars | escape | replace: '&quot;', '' | replace: '&amp;', '' | replace: '&nbsp;', '' | replace: '\', '\\\\' }}"
  }{% assign insert_comma = true %}
  {% endfor %}
]
```

{% endraw %}

相比 Simple-Jekyll-Search 提供的默认功能，我做了两处更新：

- 针对日期的过滤文章
- 增加了 `resize` 的事件处理

CSS 样式则主要参考了 [Chirpy](https://github.com/cotes2020/jekyll-theme-chirpy)，但没用 [Bootstrap](https://getbootstrap.com/) 库，我重写了核心样式：

![](/assets/img/articles-search-1.png)

同时也做了手机版的适配：

![](/assets/img/articles-search-2.png)

基本上就可以使用了。


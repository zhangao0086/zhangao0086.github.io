---
layout: post
title: "提升 Python 代码质量的工具组合"
date: 2024-10-27 23:57:40 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

# 前言

Python 这门语言优点很多，简洁、易读，在众多编程语言中脱颖而出，然而随着项目规模的扩大，代码的规范性和潜在错误成为不容忽视的问题，特别是在重构的时候，修改方法定义、删减参数量都有可能造成潜在的错误。

为了提升 Python 代码质量，我最近评测了四个工具，并最终选择了其中三个。

结论：

1. ruff，非常快，支持代码格式化和自动修复，但不支持类型检查
2. pylint，pylint 实现了许多 ruff 未实现的规则，以及更多的类型推断，比如，pylint 可以验证函数调用中的参数数量。因此 ruff 并不是 pylint 的“纯粹”替代品（反之亦然），因为它们执行了不同的规则集
3. pylance，微软官方为 VSCode 提供的 Python 插件，性能好，支持类型推断和注解检查，更重要的是能支持对整个 workspace 分析，而不是只针对当前打开的文件
4. **mypy，mypy 能直接把 python 变成静态类型的语言，非常严格，但过于严格，引入成本很多，且无法配置**

关于 ruff 的一点补充：

> Despite these differences, many users have successfully switched from Pylint to Ruff, especially those using Ruff alongside a [type checker,](https://docs.astral.sh/ruff/faq/#how-does-ruff-compare-to-mypy-or-pyright-or-pyre) which can cover some of the functionality that Pylint provides.

最终我选择：

- 用 ruff 做代码格式化、import sort
- 用 ruff + pylint 做打开文件的 lint，以 ruff 为主，覆盖 90% 的规则
- 用 pylance 做 workspace 的 lint，仅针对几个重要规则兜底，进一步增强类型检查

ruff 的配置如下，写在 pyproject.toml 文件里：

```
[tool.ruff.lint]
select = [ "F", "E", "W", "C90", "N", "YTT", "ASYNC", "PL" ]
ignore = [ "E501", "PLR2004", "PLR0913" ]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```
pylint、pylance 的配置如下，写在 VSCode 的 settings.json 文件里：
```
"editor.inlineSuggest.enabled": true,
"[python]": {
	"editor.codeActionsOnSave": {
		"source.organizeImports": "always",
	},
	"editor.formatOnSave": true,
	"editor.formatOnType": false,
	"editor.defaultFormatter": "charliermarsh.ruff",
},

"ruff.lint.run": "onType",

"python.analysis.typeCheckingMode": "off",
"python.analysis.diagnosticMode": "workspace",
"python.analysis.diagnosticSeverityOverrides": { 
	"reportArgumentType": "error",
	"reportCallIssue": "error",
	"reportAttributeAccessIssue": "error",
	"reportUnboundVariable": "error",
	"reportPossiblyUnboundVariable": "error",
},

"pylint.args": [
	"--disable=all",
	"--enable=E0611,E1123,E1101,W0613",
	"--generated-members=(cv2.*, matplotlib.*)"
]
```

举几个应用示例。

# **pylance**

例子一，定义：

```python
def function1(image_width: int, image_height: int, time: int):
    """
    方法说明
    """
    ......
```
调用：
```python
function1(
    width,
    height,
    (end_time - start_time) * 1000,
)_time(
```

因为第三个入参的类型不匹配而报错，这种情况数据一旦入库，清洗起来非常费劲：

![](/assets/img/python-lint-1.png)

例子二，list 当 dict 用了：

```python
def __create_log_file(file_path: str, schemas: list):
    """
    方法说明
    """
    functions = []
    for schema in schemas:
        type = schema["type"]
        message = schema["message"]
        params = schema["params"]
        functions.append(__create_function(type, message, params))
```

报错：

![](/assets/img/python-lint-2.png)

例子三，定义：
![](/assets/img/python-lint-4.png)

调用：
![](/assets/img/python-lint-3.png)

这就是一个明显的 bug 了，img.height 会被当作 resample 参数，而不是 size 元组。


例子四，variable possibly unbound：![img](https://alidocs.dingtalk.com/core/api/resources/img/5eecdaf48460cde56c2038a14351880d214b20080ce61bce92b39c8cc3b0b0385c532620ce754edd65a117e9692870643b321679bf759c237ca464bf163e2134224104e76cc4843e05a50d188372b3aada03a64268a0ed6c149565b860957ab4?tmpCode=7efc3166-bbd1-4372-b6d5-e3c45d63ae07)

变量 `d` 有可能未定义。

# **pylint**

例子一，keyword 参数未定义：

![](/assets/img/python-lint-5.png)

一般出现在对方法签名做了修改的时候。

例子二，导入了不存在的方法：

![](/assets/img/python-lint-6.png)

方法被移除了，该规则在重构时帮助巨大。

例子三，调用了一个不存在的方法：
![](/assets/img/python-lint-7.png)

# **ruff**

例子一，代码冗余 + 自动修复：

![](/assets/img/python-lint-8.png)


例子二，结构优化：

![](/assets/img/python-lint-9.png)


例子三，圈复杂度检测：

![](/assets/img/python-lint-10.png)

# 最后

通过结合使用 Ruff、Pylint 和 Pylance 等工具，Python 开发者可以大幅提升代码质量，这些工具各有优势，能够协同工作，为项目提供全面的代码检查和优化。虽然上述能力在其他语言中很常见，而 Python 仍需要借助社区的力量来实现，看似繁琐，但强在配置灵活，可以根据自己仓库的特点任选适合的规则。

此外，借助如今的 AI 编辑器，lint 已不仅仅只是标注错误，而是可以实现检测 + 修复一条龙实现，大大提高了效率，让开发者面对不断变化的技术环境和维护项目时更加自信。

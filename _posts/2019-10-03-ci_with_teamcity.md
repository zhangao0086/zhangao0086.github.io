---
layout: post
redirect_from: /2019/10/03/ci_with_teamcity/
title: "基于 TeamCity 的 CI 集成过程记录"
date: 2019-10-03 22:00:11 +0800
categories: [Software, CI]
article_type: 1
excerpt_separator: <!--more-->
---

目前在 TeamCity 上完成的集成有：

1. PR 接入 checks
2. 单元测试的自动化执行
3. 集成代码覆盖率报告
4. 集成测试报告

<!--more-->

# 过程思考

## PR 接入 checks

TeamCity 自带的插件就支持：<https://www.jetbrains.com/help/teamcity/pull-requests.html>

## 单元测试的自动化执行

iOS 开发下的单元测试一般是通过 xcodebuild  test 来跑，xcodebuild 依赖 scheme，scheme 只是 target 的容器，具体如何编译由 target 来决定。

为了减少配置的复杂度，我们一般是创建一个用于测试的 target 或者是一个单独的子工程，由于我们的组件化是基于 Monorepo，组件之间是隔离的，所以通过一个子工程来运行测试用例成了唯一的手段。

基于子工程测试的 workflow 为：

xcodebuild  →   TestsProject  →   scheme  →   target for tests  →   编译  →   执行测试

组件的维护者需要提供一个用于测试的工程，并在该工程内写好测试用例。

## 集成代码覆盖率报告

TeamCity 对 Java、.Net 平台有现成的插件可用，iOS 平台得自己处理，需要自己采集数据和生成报告。

代码覆盖率是编译器原生支持功能之一，其原理是先在 clang 里打桩，生成一个关于源码 range 到 count 的描述文件，由于该文件是自包含的格式，所以可以集成到 LLVM IR 和目标文件中。主要过程如下：

打桩：

```shell
clang -o test -fprofile-instr-generate -fcoverage-mapping test.c
```

集成：

```shell
llvm-profdata merge -o test.profdata default.profraw
```

输出：

```shell
llvm-cov show ./test -instr-profile=test.profdata test.c
```

由于我们是要集成到自动化工作流中，所以用 llvm-cov show 的文件输出不太合适，更好的做法是直接解析 profdata 文件，该文件是二进制的格式：<https://llvm.org/docs/CoverageMappingFormat.html>

好在有一个叫 slather 辅助工具能够帮助我们从 profdata 中采集数据，故不需要重复造轮子了。

数据采集完后，我们需要将数据生成 HTML 页面以供 TeamCity 展示。

## 集成测试报告

同样，TeamCity 只对 Java、.Net 平台有现成的支持，iOS 得自己处理，有两种处理方式：

- 生成满足要求的 XML 报告：<https://www.jetbrains.com/help/teamcity/xml-report-processing.html>
- 使用 TeamCity Service Message：<https://www.jetbrains.com/help/teamcity/build-script-interaction-with-teamcity.html#BuildScriptInteractionwithTeamCity-ReportingMessagesForBuildLog>

如果是生成 XML 报告，可以考虑使用 JUnit 的格式，这在 Java 平台适用性比较广，协议很干净。但是由于我们是基于 Monorepo，基于组件化的测试会生成多份 XML 报告，于是我们不得不在所有的测试用例跑完后，手动合并这些报告，最终给 TeamCity 提供的是一个包含了所有组件测试结果的 XML 文件。在这个方案里，大量写入 XML 文件和最终合并成一个大的 XML 文件没有太多价值，所以我们选择第二种：在测试过程中，发布 Service Message。

# 实现过程

主流程用 python 控制。

由于工程大多依赖 CocoaPods，担心 CI 的机器在 pod 更新时遇到阻碍从而影响效率，常见的阻碍是下载某一个 pod 时要么很慢、要么需要翻墙，于是先排查工程的依赖，看看存不存在这样的 pod，排查下来还真有：

```json
{
  "name": "libwebp",
  "version": "0.6.0",
  "summary": "Library to encode and decode images in WebP format.",
  "homepage": "https://developers.google.com/speed/webp/",
  "authors": "Google Inc.",
  "license": {
    "type": "BSD",
    "file": "COPYING"
  },
  "source": {
    "git": "https://chromium.googlesource.com/webm/libwebp",
    "tag": "v0.6.0"
  },
...
```

libwebp 的源码 source 指向是 googlesource.com，该地址正常在国内是无法访问的，为了避免 CI 机器翻墙，我们需要替换该 source 地址，流程如下：

- 先更新 CocoaPods 仓库：`pod repo update`
- 使用脚本替换 source：

  ```shell
  find ~/.cocoapods/repos/$REPO_NAMEA -iname libwebp -print -quit
  ```

  脚本可以直接使用 shell 或者基于 find 封装一层，因为 repos 会有多个，可以全部替换掉也可以只替换使用到的那个。这个替换操作需要在每次 pod repo update 之后执行
- 后续的主工程和测试工程一律使用 `pod update --no-repo-update` 更新

要支持自动化测试的组件需要配置 workspace、target 等字段，故设计了如下流程：

1. 在组件内定义测试用例的配置文件：coverage.json
2. 扫描 modules 下所有组件的 coverage.json，找出需要执行测试的组件
3. 调用 xcodebuild test，开启代码覆盖率收集选项，生成 LLVM Profile Data，并通过 xcpretty 发布 TeamCity Service Messagexc
4. 使用 slather 解析 LLVM Profile Data 并生成最终的报告

在这个过程中，我们针对 slather 和 xcpretty 进行了定制化开发。

## 为什么要对 slather 定制化开发？

slather 的命令行参数较冗余，在我们的 Monorepo 里，各组件下通常只有一个源码文件夹需要扫描，slather 需要添加很多 --ignore 参数，而且还只支持在当前目录下执行，意味着我们需要不停的 cd + slather、cd + slather...，除此之外，我们最终是需要将多份代码覆盖率报告整合成一份的，这就意味着 css、js 文件只需要一套，且需要一个组件索引页，也就是说哪怕我不针对 slather 进行开发，索引页这个开发工作也少不了，所以我们才最终决定对 slather 进行定制化开发。

slather 定制化的功能有：

1. 增加执行参数：--only-directory，只对需要检测的文件夹统计
2. 支持合并报告，全部页面只使用一套 css、js 文件

除此之外，slather 是基于 ruby 开发，依赖较多，且独立于每个组件单独运行，不适合生成组件索引页面，决定采用 python 来生成：

1. 使用 python 生成索引页模板：

   ```python
   def create_html_template(title):
       """
       创建 HTML 模板
       """
       return BeautifulSoup(
           f"""
           <html>
               <head>
                   <title>{title}</title>
               </head>
               <body>
                   <footer>
                   </footer>
               </body>
           </html>
           """, "html.parser"
       )
   ```

   如上，直接通过 f-Strings 写模板即可，并和 slather 共享一套资源(css、js 等)
2. 收集并汇总各组件的覆盖率数据
3. 发布 TeamCity Service Message，以报告代码覆盖率汇总结果

## 为什么要对 xcpretty 定制化开发？

xcpretty 比较成熟，虽然我们不需要生成输出文件，但是我们可以利用它对 Xcode Build Log 的解析能力快速生成 Service Message：

```ruby
def format_failing_test(classname, test_case, reason, file)
  puts "##teamcity[testStarted name='#{classname}.#{test_case}']"
  puts "##teamcity[testFailed name='#{classname}.#{test_case}' message='#{reason}' details='#{file.sub(@directory + '/', '')}']"
  puts "##teamcity[testFinished name='#{classname}.#{test_case}']"
   
  @test_count += 1
  @fail_count += 1
end
```

这是一段发布失败测试的代码样例，可以看到我们只需要在该方法调用时发布消息即可，其他的什么都不用关心。

实际上我们只需要写一个符合 xcpretty 标准的自定义 reporter，侵入性很低。

有没有其他选择呢？有，xctool 可以直接支持 TeamCity，缺点是：

- 又引入了新的工具，工具链的维护成本增加
- xctool 不支持自定义输出格式，未来拓展性较低
- xctool 不能完全代替 xcodebuild 的调用，当我们需要指定 derivedDataPath 时，需要先执行 xcodebuild，再执行 xctool

## 在 CI 的机器上需要做什么？

CI 机器只需要开启 agent，部署脚本，等待执行即可。

为了便于部署，我们创建了一个独立的仓库来维护 CI 机器所需要的功能，该仓库下的文件主要有：

- python，主控，用于执行单元测试、收集汇总结果、生成 HTML 报告、发布 TeamCity Service Message 等
- ruby
  - slather，主要用于从 LLVM Profile Data 中采集数据，基于 2.4.7 版本开发，我们提供了一个单独的 shell 脚本用于将定制化的 slather 通过 gem 安装到本机
  - xcpretty，主要用于解析 Xcode Build Log，实现了一个自定义的 reporter

部署该仓库即可，后续更新时只需要 `git pull origin master`。

## coverage.json 是干什么用的？

我们的流程需要知道哪些组件可以执行测试以及如何执行，所以在支持测试的组件根路径下添加了一个配置文件：

```json
{
 "workspace": "TestsProject.xcworkspace",
 "target": "TestsProject_Tests",
 "source_directory": "Source"
}
```

workspace 和 source_directory 填名称即可，这样整体的使用流程就是：

1. 在组件内创建一个测试工程，用于执行测试用例
2. 在组件根目录创建 coverage.json 文件
3. Done!

## 其他

技术栈上以 python 为主，引入 ruby 只是为了在现阶段完成快速开发，后续很容易将 slather(采集数据)、xcpretty(解析 Log) 替换掉。

### 如何替换 slather？

slather 的 HTML 模板以及 css 等文件我们已经不需要了，现阶段保留它只是为了采集数据，事实上 LLVM 的 API 很丰富，slather 确实不是必须的，网上有很多资料展示了如何采集数据：

- [Clang 的文档](https://clang.llvm.org/docs/SourceBasedCodeCoverage.html)
- [LLVM 的文档](https://llvm.org/docs/CommandGuide/llvm-cov.html)
- [Generate code coverage data](https://llvm.org/docs/CommandGuide/llvm-cov.html)
- 以及之前提到过的二进制格式描述：<https://llvm.org/docs/CoverageMappingFormat.html>
---
layout: post
title: "Symlinks on CocoaPods"
date: 2020-12-04 12:53:04 +0800
categories: [iOS, CocoaPods, 分享]
article_type: 1
excerpt_separator: <!--more-->
typora-root-url: ../../github.io
---

CocoaPods 是一个管理 Xcode 工程依赖的工具，其因为简单易用、功能覆盖广、拓展性强，成为了这个领域最常用的工具之一。不过想让工具完美适配各种 workflow 是不现实的，总归会有一些需要二次开发的东西，这一篇就是我们在实现环境切换时，如何利用它的特性达到最终目的的记录。

<!--more-->

# 背景

Flutter 支持三种编译模式：

- debug - 开发时使用，支持 hot reload
- profile - 用于分析性能时使用
- release - 部署到线上环境时使用

为了简化版本管理，我们会将 debug 和 release 的产物放在同一个目录下，使它们有相同的版本号，然后在应用集成时，通过环境变量决定 CocoaPods 最终的依赖目录，就像这样：

```ruby
if ENV['GD_Develop'] == nil || ENV['GD_Develop'] == '1'
	$env = 'Debug'
else
  $env = 'Release'
end

s.vendored_frameworks = "Frameworks/#$env/*.framework"
```

同时由于 Flutter 的某些版本对 IDE 的版本号有要求，如果 IDE 的版本不满足将无法打包，所以我们有一套专门构建 Flutter 包的 CI 机器，以及丰富的配置参数，用于满足开发团队的打包需求：

![image-20201205181531490](/assets/img/symlinks_on_cocoapods-1.png)

<center style="color:#999;font-size:.9em;">部分配置参数</center>

于是我们的产物仓库有的版本有 debug 制品，有的没有，这是前提。

同时我们的应用 CI 会有两种 workflow：

- dev - 用于快速 check 代码库的兼容性，以及执行一些开发模式下的检查，这个模式下不会产出包，编译的架构也有一定的裁剪
- standard - 构建 release 包，也会执行一些检查

而这两种 workflow 会自动设置不同的环境变量，这会产生一些限制：

- 只存在 release 的包将无法通过 dev 的构建
- 提测的包必须包含 release

这些限制虽然也合理，但是站在开发者的角度看，如果我这个包只是想给其他同学 review 下，应用虽然是 Release，但如果 Flutter 是 debug 包，会自带一些调试工具，协作起来可能会更方便一些。

所以我们最终在设计流程是采用了 symlink 的方式：

```bash
ln -s ./Release ./Debug
```

这样就算只产出了 release 包，也不会影响 dev 的构建。

# 实现细节

从产物的目录结构上看是符合设计的：

```bash
Frameworks
|--- Debug -> ./Release (symlink)
|--- Release
```

接下来还要继续确认 CocoaPods 对此是否有足够的支持。

根据我们对 CocoaPods 的了解，我们知道：

- CocoaPods 会将 `podspec` 缓存到本地，直到需要依赖时才去下载对应的 Pod，下载完 Pod 后会有一个预清洗的逻辑，即根据 `podspec` 的文件匹配（如 `vendored_frameworks`、`source_files` 等）语法，将不需要的文件删除，这样集成到 Xcode 工程时只需要将 Pod 目录复制过去即可
- 只有匹配成功的文件才会出现在 Pods 工程里
- 只有匹配成功的文件才会设置正确的 `search path`

所以我们会有一个 checklist：

- 检查下载的文件完整性，表现为是否包含了 Debug 和 Release 目录
- 检查文件是否正确匹配

## 检查下载的文件完整性

由于没有设置环境变量的逻辑，无论我们的 Pod 是否包含了 Release，最终一定只剩下 Debug：

```ruby
$env = 'Debug'
s.vendored_frameworks = "Frameworks/#$env/*.framework"
```

而我们需要确保 Debug 和 Release 被同时保留，然后后续根据环境变量来选择实际的依赖。

这个问题很容易解决，CocoaPods 在 `podspec` 里提供了 `preserve_paths` 配置项：

> **preserve_paths**
>
> Any file that should **not** be removed after being downloaded.
>
> ------
>
> By default, CocoaPods removes all files that are not matched by any of the other file pattern.

这样只需要添加如下配置即可：

```ruby
s.preserve_paths = 'Frameworks/**'
```

注意不能写成：

```ruby
s.preserve_paths = 'Frameworks/**/*.framework'
```

原因放到后面解释。

## 检查文件是否正确匹配

下面这段代码是 CocoaPods 读取文件系统的方法：

```ruby
# @return [void] Reads the file system and populates the files and paths
#         lists.
#
def read_file_system
	...
  escaped_root = escape_path_for_glob(root)
  Dir.glob(escaped_root + '**/*', File::FNM_DOTMATCH).each do |f|
    directory = File.directory?(f)
    # Ignore `.` and `..` directories
    next if directory && f =~ /\.\.?$/

    f = f.slice(root_length, f.length - root_length)
    next if f.nil?

    (directory ? dirs : files) << f
  end
  ...
end
```

从这段实现可以看出 CocoaPods 是支持读取 symlink 的，它会被当作正常的目录来处理。

不过最终的 files 就不一定了。

因为 symlink 实际上只是一个别名，虽然从目录结构上看是这样：

```bash
Frameworks
|--- Debug -> ./Release (symlink)
|--- |--- A.framework
```

但实际上返回的路径是 `Frameworks/Release/A.framework`，这样将匹配不到任何文件：

```ruby
$env = 'Debug'
s.vendored_frameworks = "Frameworks/#$env/*.framework"
# vendored_frameworks 将只匹配 `Frameworks/Debug` 下的 framework
```

这也是为什么在设置 `preserve_paths` 时要用 `Frameworks/**` 的原因，就是为了将 symlink 也保留下来。

用 symlink 的初衷是为了节省 CI 构建资源、产物仓库磁盘的占用以及加快 Pod 使用者的集成速度（减少了下载时间），我们的解决方案需要维持这些优点，思路有两个。

思路一，使 symlink 文件返回 symlink 目录前缀，这样后续的匹配也就正常了。不过这种方式破坏了 symlink 自身的语义，而且需要修改 CocoaPods 的源码，可以说是费力不讨好，难度 **Hard**。

思路二，将 symlink 变成实际的物理目录 - 需要找准时机，在 Pod 下载后和 Pod 集成前，难度 **Easy**。

根据思路二可以找到好几个时机，不过最完美的当属 CocoaPods 自身提供的 `prepare_command`：

> **prepare_command**
>
> A bash script that will be executed after the Pod is downloaded. This command can be used to create, delete and modify any file downloaded and will be ran before any paths for other file attributes of the specification are collected.
>
> This command is executed before the Pod is cleaned and before the Pods project is created. The working directory is the root of the Pod.
>
> If the pod is installed with the `:path` option this command will not be executed.

最终可以这样去解决：

```ruby
s.prepare_command = <<-CMD
                  if [[ -L \"Frameworks/Debug\" ]]; then
                    rm -rf Frameworks/Debug
                    cp -r Frameworks/Release Frameworks/Debug
                  fi
                      
                  if [[ -L \"Frameworks/Release\" ]]; then
                    rm -rf Frameworks/Release
                    cp -r Frameworks/Debug Frameworks/Release
                  fi
              CMD
```

# 总结

这篇文章记录了在建立 Flutter CI 系统构建 iOS 产物时，由于一个场景问题引发的一系列思考，在寻找最终解决方案的过程中，每一步我们都希望能做到最好，并保持最简单的实现：

- symlink 配合 `vendored_frameworks`、`preserve_paths` 适配构建场景
- 使用 `prepare_command` 预处理 symlink

仅此而已。
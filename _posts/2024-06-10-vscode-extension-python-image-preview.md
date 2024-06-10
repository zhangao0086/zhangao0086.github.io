---
layout: post
title: "分享一次 VS Code 插件开发过程"
date: 2024-06-10 22:59:44 +0800
categories: [分享]
article_type: 1
typora-root-url: ../../github.io
---

![](/assets/img/vscode-extension-python-image-preview-caption.png)

最近工作较多用到 Python 的图像处理，也就是这些库：

- [Pillow](https://github.com/python-pillow/Pillow)：强大的 Python 图像处理库，支持打开、操作和保存各种图像文件格式，是 PIL（Python Imaging Library）的友好分支
- [opencv](https://github.com/opencv/opencv-python)：开源的计算机视觉和机器学习库，提供了丰富的图像和视频处理能力
- [numpy](https://github.com/numpy/numpy)：一个基础科学计算库，能对多维数组、矩阵进行高效运算，内置了大量的数学函数库

这些库很强大，但是在开发过程中，如果想近距离观察它们的输入、对图像的影响，就不太方便了，通常你需要将它们转存到文件系统中以便观察：

```python
# PIL
image.save("/path/to/save", "png")

# cv2
cv2.imwrite("/path/to/save", image)

# numpy
pil_image = Image.fromarray(image_np)
pil_image.save("/path/to/save", "png")
```

在实际开发中，有两种方式可以做到：

1. 在 repl 环境中输入指令，临时的，无法连续执行
2. 修改代码，然后重新运行，有时候需要来回多次

无论哪种都很不便，这个场景特别适合用 VS Code 插件解决，趁端午放假学习了下，主要过程：

1. 开发环境搭建
2. 熟悉基本的插件 debug 方法
3. 在右键菜单中添加一个预览图像的入口，点击后打开新 tab
4. 将图像数据传输到插件（以 PIL 为例）
5. 在新 tab 中预览图像

第 1、2 步跟着官方教程 [Your First Extension](https://code.visualstudio.com/api/get-started/your-first-extension) 来就行了，VS Code 提供了非常便利的开发环境，虽然插件和宿主程序在不同的进程，但 debug 起来无缝，效率很高。

第 3 步需要做些调研，在 [Contribution Points](https://code.visualstudio.com/api/references/contribution-points) 找到你最期望的交互时机，我选择了 `editor/context`，这个是时机的好处是可以基于用户选择的文本，灵活地创建预览图像：

```json
"contributes": {
  "commands": [
    {
      "command": "cvimagepreviewer.preview",
      "title": "Preview as Image"
    }
  ],
  "menus": {
    "editor/context": [
      {
        "when": "editorLangId == python",
        "command": "cvimagepreviewer.preview",
        "group": "z_commands"
      }
    ]
  }
},
```

```typescript
const editor = vscode.window.activeTextEditor;
if (editor) {
    const selection = editor.selection;
    const selectedText = editor.document.getText(selection);
}
```

比如下面这行代码：

```python
mask = ImageChops.lighter(alpha_mask, mask.convert('L')).convert('L')
```

`alpha_mask`、`mask` 和 `lvalue mask` 是变量，`mask.convert('L')` 是中间变量，如果想对 `convert` 的中间转换结果做预览，`selectedText` 就会非常有用，你只需要将 `selectedText` 当作一个表达式求值即可，无论它是一条语句还是一个变量。

对表达式求值可以使用 `customRequest` 的 `evaluate` 请求，从这里开始就是第 4 步的内容了，主要是解决插件与宿主程序的通信问题：

```typescript
const debugSession = vscode.debug.activeDebugSession;
const response = await debugSession.customRequest('evaluate', {
	expression,
	frameId,
	context: 'repl'
});
```

`customRequest` 支持的 Request、以及对应的 Response 完整清单可以参见 [Debug Adapter Protocol](https://microsoft.github.io/debug-adapter-protocol/specification)。

比较麻烦的是 `frameId` 的获取，由于多线程的原因，你不能假设表达式一定可以在 Main 线程执行，像 [Gradio](https://www.gradio.app/)、[Flask](https://flask.palletsprojects.com/) 等都是以 worker 线程的方式执行任务的，在早期的 VS Code 版本中，得通过 `threads`、`stackTrace`、`scopes` 一层一层来找，过程中涉及大量的插件与宿主程序之间的通信，最终再通过解析所有的局部变量、全局变量找到对应的 `frameId`。

幸运的是 VS Code 1.90 版本（2024 年 5 月发布）刚刚添加了一套新的 [Debug Stack Focus API](https://code.visualstudio.com/updates/v1_90#_debug-stack-focus-api)，新增的 `activeStackItem` 可以直接获取当前的 thread or stack frame：

```typescript
const activeStackItem = vscode.debug.activeStackItem;
let frameId = undefined
if (activeStackItem instanceof vscode.DebugStackFrame) {
    frameId = activeStackItem.frameId;
}
```

>顺便在 Stack Overflow 上水了个回答：[VS code API: How to get thread id on which debugger is paused in multithread program](https://stackoverflow.com/questions/77478171/vs-code-api-how-to-get-thread-id-on-which-debugger-is-paused-in-multithread-pro)

这种做法有利有弊：

- 利，可以精准的在指定线程执行表达式，拿到想要的图像数据
- 弊，以往按 `threads`、`stackTrace` 遍历的方式虽然低效，但能一次性将全部的图像变量都找出来，批量预览，看起来很酷

具体权衡就看自己如何选择了。

除了 `frameId` 外，`expression` 也有点难搞，通过 repl 执行的表达式，如果是多行语句，那么拿不到最后一条语句的执行结果，以 PIL 为例：

```python
import base64
from io import BytesIO

buffered = BytesIO()
${expression}.save(buffered, format="PNG")
base64.b64encode(buffered.getvalue())
```

期望是得到 PIL 图像的 Base64 数据，但实际上什么也得不到，三种解决方案：

1. 提前封装一些 python 函数，把你针对 PIL、opencv 等等需要的代码封装好，再通过 VS Code 提供的 [TextEdit](https://code.visualstudio.com/api/references/vscode-api#TextEdit) 接口注入进去，需要用时用单条语句调用即可
2. 和上面差不多，不用提前注入，分成两次执行即可，第一次执行把结果缓存在变量中，第二次执行直接取变量值，拿上述代码来说，最后一行改为 `img_str = base64.b64encode(buffered.getvalue())`，然后第二次执行直接获取 `img_str`
3. 不返回结果，用文件系统作为传输介质，把图像写到指定位置，事后清理

第 5 步就比较简单了，如果是文件系统，直接用 `vscode.open` 开一个边窗展示：

```typescript
const options = {
    viewColumn: vscode.ViewColumn.Beside,
    preview: preview,
    preserveFocus: true,
};
return vscode.commands.executeCommand(
    "vscode.open",
    vscode.Uri.file(path),
    options
);
```

如果是 Base64，创建一个 `WebviewPanel` 并用 [WebView](https://code.visualstudio.com/api/ux-guidelines/webviews) 展示：

```typescript
function getWebviewContent(imageData: string): string {
    return `
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Image Preview</title>
    </head>
    <body>
        <img src="${imageData}" width="100%" height="100%"/>
    </body>
    </html>`;
}
```

相比插件本身，让人印象更深刻的是 VS Code 插件系统的设计和生态系统。它不仅功能强大，提供了丰富的 API 带来无限的扩展性，同时其易用性、完善的文档和工具也令人赞叹。正是这些特点，使得任何人都能轻松上手并创建出自己想要的插件，从而为全球开发者提供了一个强大且灵活的平台，实现了开发者生产力提升、开发者社区繁荣的双赢。

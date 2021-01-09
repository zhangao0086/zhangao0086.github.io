---
layout: post
redirect_from: /2019/08/03/The-most-important-skill-a-programmer-can-learn
title: "The most important skill a programmer can learn"
date: 2019-08-03 16:43:20 +0800
disable_excerpt: false
categories: [Software]
article_type: 3
---


> *Originally published at [https://huseyinpolatyuruk.com](<https://huseyinpolatyuruk.com/2019/05/03/the-most-important-skill-a-programmer-can-learn/>).*



![The Most Important Skill a Programmer Can Learn](https://cdn-media-1.freecodecamp.org/images/0*XG0c4KW0GKI5h3Sq)

**No, no, no, no, and no. And no.**

A big NO. Clear as that.

All you have to do is to bring those two-letters together and say it.

Now, let’s say it together. NOOOOOOO!

这是一个很好的开始.

但是等一等，什么时候对什么说 NO 呢？

嗯，这是大多数程序员（甚至是资深程序员）容易迷惑的地方。

作为一个程序员，写代码是工作中最重要的部分，在编程的生命周期内，你将不得不处理很多不同的代码请求，每个请求都会迫使你做艰难的决策。这当然没有错，这正是大家对你的期望，作为一个程序员：写代码，天经地义。然而，有一个问题：你是否应该编写被要求的所有代码呢？

这个问题将我们带到程序员能学习到的最重要的技能上：

> *知道什么时候不写代码可能是一个程序员能学习到的最重要的技能. —* [*The Art Of Readable Code*](https://www.amazon.com/Art-Readable-Code-Practical-Techniques/dp/0596802293)

我不能同意更多。为什么呢？

编程是解决问题的艺术，所以很自然的，程序员是解决问题的人。作为程序员，当我们面对一个需要解决的新问题或者其他原因需要写代码时，我们会感到兴奋。

这当然没关系，因为我们是程序员，我们喜欢写代码。

然而，对写代码过于兴奋可能会使我们盲目。它让我们忽略了一些重要的事情，这可能在未来导致大问题。

所以，这些被忽略的重要的事情是什么呢？

你写下的每一行代码都是:

- 会被其他程序员阅读和理解的
- 会被测试和调试的
- 会潜在增加软件的缺陷
- 可能会在未来引入新的 Bugs

就像 Rich Skrenta 在 [code is our enemy](https://www.skrenta.com/2007/05/code_is_our_enemy.html) 里写的：

> *代码不好，它需要定期维护，它隐藏着 Bugs 等你发现，增加新功能意味着有老代码必须被调整.*
>
> *你的代码量越大，隐藏的 Bugs 就越多，checkout 的时间和编译的时间就越长，新员工需要更多的时间理解现有的系统，如果要重构，那么就有更多东西要频繁移动.*
>
> *此外，代码量大通常意味着灵活性差，这是反直觉的，但很多时候，一个简单、优雅的解决方案比混乱、庞杂的代码要更快更通用.*
>
> *代码是由工程师产出的，要产出更多代码，就需要更多工程师，工程师之间有 $$ n^{2}$$ 的沟通成本，代码越大，成本越大.*

很正确，不是吗？能增加开发效率和灵感的程序员正是那些知道什么时候说 NO 的程序员，易于维护、长期运行、能不断帮助用户的软件是没有不必要的代码的。

> *The best code is no code at all and the most effective programmer is the one who knows when not to code.*

## 你怎么知道何时不需要代码?

当你在一个项目上开发并想像要实现的功能时，很自然会感到兴奋，但是程序员往往倾向于高估项目实际所需要的功能，许多功能未完成或者没有使用过或者只是让程序过于复杂，你应用知道什么对你的项目是至关重要的，以避免这个坑。

> *理解软件的目的和核心定义是知道何时不需要代码的第一步.*

让我给你举个例子吧，比如说你的软件只有一个核心定义：管理邮件。那么收、发邮件是两个基本的功能，你不能指望这个软件也可以管理 To-Do List，对吧？

那么对于与这个定义无关的功能请求，你应该说 NO。现在你知道了何时不需要代码：

> *永远不要拓展软件的用途.*

一旦你知道你的项目核心是什么，你就会有意识地去评估功能请求，你会精确的知道哪些功能应该被实现，哪些代码应该被编写，因为你知道不必要的代码会杀掉这个项目。

> *知道什么时候不需要代码能让你的代码库变少*

![img](https://cdn-media-1.freecodecamp.org/images/AaXgIsHTyVquQeabDnz5kMCsyEmPuMnod3E9)

在项目刚启动时，你知道两、三个源文件，看起来很简单，编译和运行只需要几秒钟，你知道在哪里能找到你想要的东西。

之后这个项目增长了，越来越多的源文件被加进了目录，每个文件包含几百行代码，为了管理它们，你需要更多的目录。记住函数的调用关系变得很难，跟踪 Bugs 需要更多时间，随着项目管理的困难，你需要更多的程序员，然后随着程序员的增加，[沟通成本](https://en.wikipedia.org/w/index.php?title=Communication_overhead&action=edit&redlink=1)也会增加。你变得越来越慢。

最终，这个项目变得庞大，增加新功能变得很痛苦，即时是小的改变也需要几个小时，修复问题问题会引起新的问题，你开始错过 deadlines...

现在，生活对你来说像是一场战争。这是为什么？

因为你知道什么时候不需要代码。你对每一个功能都说 YES，你盲目了，你忽略了那些重要的事情。

这就像一部恐怖电影，对吧？

如果你总是说 YES，这就是你会面对的情况，知道什么时候不要写代码，尽可能消除项目中不需要的代码，会使生活更轻松，也能让项目持续的时间更长。

> *我最有效率的一天，删除了 1000 行代码. — Ken Thompson*

我知道要清楚的知道什么时候不需要代码是很难的，即使是资深程序员。也许，我在本文中写的内容对初始程序员来说很难理解，这是我能够理解的。

我知道你刚刚才开始编程，你想定代码，你对此很兴奋，这很好，永远不要失去这种兴奋感，但也永远不要忽略那些重要的事。我们总是在犯错后学习，你也会犯错误，你也会从中吸取教训，但至少，你可以有意识地从我的经验中学习。

> *Keep coding but know when to say no to coding.*
---
layout: post
title: 'Swift Nullability and Objective-C'
date: 2015-03-18 18:59:51
categories: [iOS,Swift]
csdn_read_num: 6436
article_type: 1
---


﻿通过Bridging-Header文件，Swift可以与Objective-C无缝调用，但是Swift与Objective-C有一个很大的不同点：Swift支持`Optional`类型。比如`NSView`和`NSView?`，在Objective-C里对此只有一种表示，即`NSView *`，既可以用来表示该View为nil、也能表示为非nil，此时Swift编译器是无法确定这个NSView是不是`Optional`类型的，这种情况下Swift编译器会把它当作`NSView!`处理，隐式拆包。

在早期发布的Xcode版本中，苹果的一些框架针对Swift的Optional类型进行了一些专门审查，使他们的API能够适配Optional，而Xcode 6.3的发布，给我们带来了Objetive-C的一个新特性：`nullability`注解，利用该特性我们也能对自己的代码进行类似的处理。

## 核心：__nullable 和 __nonnull ##
这个功能给我们带来了两个新的类型注解：`__nullable`和`__nonnull`，就像你看到的，`__nullable`可以表示一个`NULL`或者`nil`值，而`__nonnull`则刚好相反。如果你违反了这个规则，你将会收到编译器的警告：

```objective-c
@interface AAPLList : NSObject <NSCoding, NSCopying>
//---
- (AAPLListItem * __nullable)itemWithName:(NSString * __nonnull)name;
@property (copy, readonly) NSArray * __nonnull allItems;
//---
@end

//--------------

[self.list itemWithName:nil]; // warning!
```

你能在任何地方使用`__nullable`和`__nonnull`关键字，比如和标准C的`const`一起使用，也能直接应用到指针上。但是在大多数情况下，你会以优雅的方式写下这些注解：在方法定义或声明里，只要类型是一个简单的对象或者Block指针，你就能以***不带下划线***的方式(`nullable`或`nonnull`)直接写在左括号后面：

```objective-c
- (nullable AAPLListItem *)itemWithName:(nonnull NSString *)name;
- (NSInteger)indexOfItem:(nonnull AAPLListItem *)item;
```

对于`@property`，你也能以同样的方式写在它的属性列表里：

```objective-c
@property (copy, nullable) NSString *name;
@property (copy, readonly, nonnull) NSArray *allItems;
```

不带下划线的形式比带下划线的形式看起来更简洁，但你仍然需要将它们应用到头文件的每一个类型里。如果你觉得麻烦同时想让头文件变得更加简洁，你就会使用到审查区域。

## 审查区域（Audited Regions） ##
如果想更加轻松的添加这些注解，那么你可以把Objective-C头文件的某个区域标记为需要审查(for nullability)，在这个区域内，所有简单的指针类型都会被当作`nonnull`，我们之前的例子会变成这样：

```objective-c
NS_ASSUME_NONNULL_BEGIN
@interface AAPLList : NSObject <NSCoding, NSCopying>
//---
- (nullable AAPLListItem *)itemWithName:(NSString *)name;
- (NSInteger)indexOfItem:(AAPLListItem *)item;

@property (copy, nullable) NSString *name;
@property (copy, readonly) NSArray *allItems;
//---
@end
NS_ASSUME_NONNULL_END

// --------------

self.list.name = nil;   // okay

AAPLListItem *matchingItem = [self.list itemWithName:nil];  // warning!
```

> Xcode 6.3（iOS 8.3 SDK）引入了`NS_ASSUME_NONNULL_BEGIN / END`宏
其中itemWithName方法的name参数没有使用Nullability特征，但是会被当作`nonnull`处理

为了安全起见，这个规则也有一些例外情况：

- `typedef`定义的类型不会继承`nullability`特性—它们会轻松地根据上下文选择nullable或non-nullable，所以，就算是在审查区域内，`typedef`定义的类型也不会被当作`nonnull`。
- 像`id *`这样更复杂的指针类型必须被显式地注解，比如，你要指定一个nonnull的指针为一个nullable的对象引用，那么需要使用`__nullable id * __nonnull`。
- 像`NSError **`这些特殊的、通过方法参数返回错误对象的类型，将总是被当作是一个nullable的指针指向一个nullable的指针：`__nullable NSError ** __nullable`。

你可以通过<a href="http://developer.apple.com/go/?id=error-handling-cocoa" target="_blank">Error Handling Programming Guide</a>了解更多详细内容。

## 兼容性 ##
你的Objective-C框架现有的代码写对了吗?是否能安全的改变它们的类型? *Yes, it is*.

- 现有的、被*编译过*的代码还能继续使用你的框架，也就是说<a href="https://developer.apple.com/library/ios/documentation/Xcode/Conceptual/iPhoneOSABIReference/Introduction/Introduction.html" target="_blank">ABI</a>没有变化（编译器不会报错），这也意味着现有的代码不会在运行时捕获到`nil`的不正确传值。
- 用新的Swift编译器编译现有的*源码*，并在使用你的框架的时候，可能会因为一些不安全的行为在编译时得到额外的警告。
- `nonnull`不影响优化，尤其是你还可以在运行时检查标记为`nonnull`的参数是否为`nil`，这可能需要必要的向后兼容。

大多数情况下，应该接受`nullable`和`nonnull`，你当前所使用的断言或者异常太粗暴了：违反约定是程序员经常犯的错误（而`nullable`和`nonnull`能在编译时就解决问题）。特别的，返回值是你能控制的东西，永远不应该对一个non-nullable的返回类型返回一个`nil`，除非这是为了向后兼容。

## 回到Swift ##
现在我们给我们的Objective-C头文件添加了nullability注解，我们在Swift中使用它：
在Objective-C中添加注解之前：

```swift
class AAPLList : NSObject, NSCoding, NSCopying { 
	//---
	func itemWithName(name: String!) -> AAPLListItem!
	func indexOfItem(item: AAPLListItem!) -> Int

	@NSCopying var name: String! { get set }
	@NSCopying var allItems: [AnyObject]! { get }
	//---
}
```

添加注解之后：

```swift
class AAPLList : NSObject, NSCoding, NSCopying { 
	//---
	func itemWithName(name: String) -> AAPLListItem?
	func indexOfItem(item: AAPLListItem) -> Int

	@NSCopying var name: String? { get set }
	@NSCopying var allItems: [AnyObject] { get }
	//---
}
```

这些Swift代码非常清晰。只有一些细节的变化，但是它让你的框架使用起来更爽。

---
layout: post
title: 'Swift Core Data 图片存储与读取Demo'
date: 2015-03-20 23:08:37 +0800
categories: [iOS,Swift]
csdn_read_num: 9928
article_type: 1
---


﻿实体的模型定义：
[外链图片转存中...(img-ORS7oN2q-1562249788653)]

[外链图片转存中...(img-vtM3HeXk-1562249788654)]

实体的class定义：

```swift
@objc(ImageEntity)
class ImageEntity: NSManagedObject {
    @NSManaged var imageData: NSData
}
```

存储：

```swift
@IBAction func saveImageToCoreData() {
    let delegate = UIApplication.sharedApplication().delegate as AppDelegate
    let context = delegate.managedObjectContext
    
    let imageData = UIImagePNGRepresentation(UIImage(named: "image"))
    
    let imageEntity = NSEntityDescription.entityForName("ImageEntity", inManagedObjectContext: context!)
    let image = ImageEntity(entity: imageEntity!, insertIntoManagedObjectContext: context!)
    image.imageData = imageData
    
    var error: NSError?
    if context!.save(&error) == false {
        println("failed: \(error!.localizedDescription)")
    }
}
```

读取：

```swift
@IBAction func loadImageFromCoreData() {
    let delegate = UIApplication.sharedApplication().delegate as AppDelegate
    let context = delegate.managedObjectContext
    
    let request = NSFetchRequest(entityName: "ImageEntity")
    var error: NSError?
    let imageEntities = context?.executeFetchRequest(request, error: &error)
    
    let imageEntity = imageEntities?.first! as ImageEntity
    self.imageView.image = UIImage(data: imageEntity.imageData)
}
```

## <a target="_blank" href="https://github.com/zhangao0086/CoreDataSaveImageDemo">Demo地址</a> ##

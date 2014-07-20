import imagedb

testImages = {
    '/home/hi117/Pictures/wallpaper-2471485.png': ['test', 'Chuuni'],
    '/home/hi117/Pictures/yande.re 229970 sample.jpg': ['test', 'LB'],
    }

ids = []

print 'Testing Adding Images'
for i in testImages:
    print i
    t = imagedb.addImage(open(i).read(), testImages[i])
    ids.append(t[0])
    print t

print 'Testing listing tags'
tags = imagedb.listTags()
print tags
for i in tags:
    print imagedb.getTag(i)

print 'Testing removing images'
for i in ids:
    print i
    imagedb.removeImage(i)

print 'Testing removing tags'
for i in tags:
    print i
    imagedb.removeTag(i)

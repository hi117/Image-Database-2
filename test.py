import imagedb

testImages = {
    '/home/hi117/Pictures/wallpaper-2471485.png': ['test', 'Chuuni'],
    '/home/hi117/Pictures/yande.re 229970 sample.jpg': ['test', 'LB'],
    }

for i in testImages:
    print i
    print imagedb.addImage(open(i).read(), testImages[i])


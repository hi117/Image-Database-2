# cleans the database
import imagedb
images = imagedb.images
for i in images.view('imagedb/links'):
    images.delete(images[i.id])

docs = []
for i in images.view('imagedb/tags'):
    doc = images[i.id]
    doc['images'] = []
    docs.append(doc)
images.update(docs)

for i in images.view('imagedb/images'):
    images.delete(images[i.id])

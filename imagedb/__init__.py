from PIL import Image
from StringIO import StringIO
import imagedb.links
import imagehash
import json
import subprocess
import re
import numpy
import tempfile
import hashlib
import zlib
import config

images = config.images

class NoTags(Exception):
    pass

class Exists(Exception):
    pass

class NoDocument(Exception):
    pass

class InvallidType(Exception):
    pass

def genTagsFromLinks(tags, links):
    return tags, links

def checkCollision(hashes):
    out = {}
    for i in hashes:
        v = images.view('hashes/' + i, key=hashes[i])
        for j in v:
            if not j.id in out:
                out[j.id] = 0
            out[j.id] += 1
    rout = []
    for i in out:
        if out[i] == len(hashes):
            rout.append(i)
    return rout

def imageHashToInt(h):
    n = 0
    for i in h.hash.flatten():
        n = n*2
        if i:
            n+=1
    return n

def distance(a, b, bits=32):
    x = (a ^ b) & ((1 << bits) - 1)
    tot = 0
    while x:
        tot += x & 1
        x >>= 1
    return tot

def checkPhash(hash):
    out = []
    hash = int(hash)
    for i in images.view('hashes/phash'):
        if distance(hash, int(i.key), 64) <= 3:
            out.append(i.id)
    return out

def mDelete(id):
    '''
    Marks an image for cleanup and deletion.
    '''
    if not id in images:
        raise NoDocument()

    doc = images[id]
    doc['delete'] = True
    images.save(doc)

def addImage(image):
    '''
    Adds an image.
    '''
    doc = {'type': 'image', 'tags': [], 'links': []}

    # Generate the PIL image
    f = tempfile.NamedTemporaryFile()
    f.write(image)
    f.flush()
    f.seek(0)
    im = Image.open(f)

    # Calculate the hashes
    hashes = {}
    hashes['length'] = len(image)

    hashes['crc32'] = hex(zlib.crc32(image) & 0xffffffff)[2:]
    hashes['md5'] = hashlib.md5(image).hexdigest()
    hashes['sha1'] = hashlib.sha1(image).hexdigest()
    hashes['sha256'] = hashlib.sha256(image).hexdigest()
    hashes['sha512'] = hashlib.sha512(image).hexdigest()
    collisions = checkCollision(hashes)
    
    hashes['phash'] = str(imageHashToInt(imagehash.phash(im)))
    pcollisions = checkPhash(hashes['phash'])
    
    doc['hashes'] = hashes

    # Generate a thumbnail
    im.thumbnail(config.thumbsize)
    thumb = StringIO()
    im.convert('RGB').save(thumb, "JPEG")

    # Get exif and mime
    doc['exif'] = json.loads(subprocess.check_output(['exiftool', '-j', f.name]))[0]
    for i in config.exifIgnore:
        doc['exif'].pop(i)
    doc['mime'] = subprocess.check_output(['file', '--mime-type', f.name]).split(' ')[1][:-1]
    id = images.save(doc)[0]
    thumb = thumb.getvalue()
    images.put_attachment(images[id], thumb, filename = 'thumbnail.jpg', content_type =  config.thumbMime)
    images.put_attachment(images[id], image, filename='image', content_type=doc['mime'])
    return id, collisions, pcollisions

def removeImage(id):
    '''
    Removes an image from the database.
    '''
    # Check if id exists and is an image.
    if not id in images:
        raise NoDocument()
    doc = images[id]
    if not 'type' in doc or doc['type'] != 'image':
        raise InvallidType()

    # Remove the image from all tags.
    for i in doc['tags']:
        removeFromTag(id, i)

    # Remove the image from all links
    for i in doc['tags']:
        imagedb.links.removeFromLink(id, i)

    images.delete(images[doc.id])


def addTag(tag, hidden=False):
    '''
    Adds a tag, optionally hidden.
    Returns the created id.
    '''
    if tag in listTags():
        raise Exists()
    return images.save({'type': 'tag', 'name': tag, 'hidden': hidden, 'images': []})[0]

def removeTag(tag):
    '''
    Removes a tag.
    '''
    # Check if tag actually exists.
    tags = listTags()
    if not tag in tags:
        raise NoDocument()

    # Loop over all images in the tag, removing the tag from the images.
    tag = tags[tag]
    doc = images[tag]
    docs = [doc]
    for image in images[tag]['images']:
        i = images[image]
        i['tags'].remove(tag)
        docs.append(i)

    # Save the result.
    images.update(docs)
    images.delete(images[tag])

def addToTag(image, tag):
    '''
    Adds an image to a given tag.
    Tag is in name or id form.
    '''
    # Check if the image exists.
    if not image in images:
        raise NoDocument()

    # Check if the tag exists and if it doesnt, create it
    if tag in images:
        tag = images[tag]
    else:
        tag = images[getTag(tag)]

    imaged = images[image]
    imaged['tags'].append(tag['_id'])
    tag['images'].append(image)
    images.update([tag, imaged])

def removeFromTag(image, tag):
    '''
    Removes an image from a given tag.
    Tag is in name or id form.
    '''
    # Check if image exists.
    if not image in images:
        raise NoDocument()

    # Translate tag to an id.
    if not tag in images:
        tag = getTag(tag)

    image = images[image]
    tag = images[tag]
    image['tags'].remove(tag['_id'])
    tag['images'].remove(image['_id'])
    images.update([image, tag])

def getTag(tag, id=False):
    '''
    if id is False, translates a tag name to a tag id.
    If id is True, translates a tag id to a tag name.
    '''
    if not id:
        try:
            return listTags(tag=tag)[tag]
        except NoDocument as e:
            return addTag(tag)
    else:
        if not tag in images:
            raise NoDocument()
        doc = images[tag]
        if doc['type'] != 'tag':
            raise InvallidType()
        return doc['name']

def listTags(reverse=False, tag=None, hidden=False):
    '''
    Returns a list of tags in name indexed order.
    '''
    if hidden:
        return images.view('imagedb/hiddenTags')
    o = {}
    if tag:
        v = images.view('imagedb/tags', key=tag)

        if len(v) == 0:
            raise NoDocument()
    else:
        v = images.view('imagedb/tags')

    if not reverse:
        for i in v:
            o[i.key] = i.id
    else:
        for i in v:
            o[i.id] = i.key
    return o

def getImage(image, type='doc'):
    '''
    Returns an image defined by id.
    if type is doc, returns the document.
    if type is thumb, returns the thumbnail.
    if type is image, returns the image.
    '''
    if not image in images:
        raise NoDocument()

    i = images[image]
    if not 'type' in i and i['type'] == 'image':
        raise InvallidType()

    if type == 'doc':
        return i
    if type == 'thumb':
        return images.get_attachment(i, 'thumbnail.jpg')
    if type == 'image':
        return images.get_attachment(i, 'image'), i['_attachments']['image']['content_type']
    raise ValueError()

def listImages():
    '''
    idk
    '''
    return images.iterview('imagedb/images', 100)

def get(id):
    '''
    Returns a document from the image database.
    '''
    if id in images:
        return images[id]
    raise NoDocument()

def isHidden(id):
    '''
    Returns True if doc is hidden, False otherwise.
    If id is an image, checks all tags to see if any are marked hidden.
    if id is a tag, checks the hidden attribute.
    '''
    if not id in images:
        raise NoDocument()

    doc = images[id]
    if not 'type' in doc and (doc['type'] == 'image' or doc['type'] == 'tag'):
        raise InvallidType()

    # doc is a tag
    if doc['type'] == 'tag':
        return doc['hidden']

    hidden = listTags(hidden=True)
    if len(hidden) == 0:
        return False
    hidden = map(lambda a: a.id, hidden)
    # doc is an image
    for i in doc['tags']:
        if i in hidden:
            return True
    return False

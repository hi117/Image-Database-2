from PIL import Image
from StringIO import StringIO
import imagehash
import couchdb
import json
import subprocess
import re
import numpy
import tempfile
import hashlib
import zlib

couch = couchdb.Server('http://127.0.0.1:5984')
images = couch['imagedbnew']

thumbSize = (128, 128)

exifIgnore = [
        "SourceFile",
        "ExifToolVersion",
        "FileName",
        "Directory",
        "FileSize",
        "FileModifyDate",
        "FileAccessDate",
        "FileInodeChangeDate",
        "FilePermissions",
        "FileType",
        "MIMEType",
        ]

cryptoHashes = [
        "crc32",
        "md5",
        "sha1",
        "sha256",
        "sha512",
        ]

scores = {
        'crc32': 50,
        'md5': 100,
        'sha1': 150,
        'sha256': 200,
        'sha512': 250,
        'phash': 20,
        'dhash': 10,
        'ahash': 5,
        }

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

def checkCollision(type, hash, length=0):
    if type in cryptoHashes:
        v = images.view('hashes/' + type, key=hash)
        if v.total_rows > 0:
            for i in v:
                if i.value == length:
                    return scores[type]
    else:
        v = images.view('hashes/' + type, key=hash[1])
        if v.total_rows > 0:
            for i in v:
                if hashToImagehash(i.value) - hashToImagehash(hash[0]) <= 3:
                    return scores[type] * (5 - (hashToImagehash(i.value) - hashToImagehash(hash[0])))
    return 0

def hashToImagehash(h):
    a = []
    for i in re.findall('..', h):
        b = []
        for j in range(8):
            b.append(bool(int('0x' + i, 16) & 2**j))
        a.append(b)
    return imagehash.ImageHash(numpy.array(a, dtype=bool))

def addImage(image, tags=[], links=[]):
    '''
    Adds an image.
    '''
    doc = {'type': 'image'}
    # An image must have tags, either generated from links or provided
    if len(links) == 0:
        tags, doc['links'] = genTagsFromLinks(tags, links)
    if len(tags) == 0:
        raise NoTags()

    # Translate the tags into ids
    sTags = listTags()
    doc['tags'] = []
    for i in tags:
        if not i in sTags:
            sTags[i] = addTag(i)
        doc['tags'].append(sTags[i])

    # Generate the PIL image
    f = tempfile.NamedTemporaryFile()
    f.write(image)
    f.flush()
    f.seek(0)
    im = Image.open(f)

    # Calculate the hashes
    # NOTE: for perceptiual hashes that are used in hamming distance 
    # calculations, a second hash, the count of true bits, is stored to make
    # lookups faster, this is useless for cryptographic ones though
    score = 0
    hashes = {}
    hashes['length'] = len(image)
    hashes['crc32'] = hex(zlib.crc32(image) & 0xffffffff)[2:]
    score += checkCollision('crc32', hashes['crc32'], hashes['length'])
    hashes['md5'] = hashlib.md5(image).hexdigest()
    score += checkCollision('md5', hashes['md5'], hashes['length'])
    hashes['sha1'] = hashlib.sha1(image).hexdigest()
    score += checkCollision('sha1', hashes['sha1'], hashes['length'])
    hashes['sha256'] = hashlib.sha256(image).hexdigest()
    score += checkCollision('sha256', hashes['sha256'], hashes['length'])
    hashes['sha512'] = hashlib.sha512(image).hexdigest()
    score += checkCollision('sha512', hashes['sha512'], hashes['length'])

    phash = imagehash.phash(im)
    phashH = phash.hash.sum()
    hashes['phash'] = [str(phash), phashH]
    score += checkCollision('phash', hashes['phash'])
    ahash = imagehash.average_hash(im)
    ahashH = ahash.hash.sum()
    hashes['ahash'] = [str(ahash), ahashH]
    score += checkCollision('ahash', hashes['ahash'])
    dhash = imagehash.dhash(im)
    dhashH = dhash.hash.sum()
    hashes['dhash'] = [str(dhash), dhashH]
    score += checkCollision('dhash', hashes['dhash'])
    
    doc['hashes'] = hashes

    # Generate a thumbnail
    im.thumbnail(thumbSize)
    thumb = StringIO()
    im.convert('RGB').save(thumb, "JPEG")

    # Get exif and mime
    doc['exif'] = json.loads(subprocess.check_output(['exiftool', '-j', f.name]))[0]
    for i in exifIgnore:
        doc['exif'].pop(i)
    doc['mime'] = subprocess.check_output(['file', '--mime-type', f.name]).split(' ')[1][:-1]
    id = images.save(doc)[0]
    tags = []
    for i in doc['tags']:
        t = images[i]
        t['images'].append(id)
        tags.append(t)
    images.update(tags)
    thumb = thumb.getvalue()
    images.put_attachment(images[id], thumb, filename = 'thumbnail.jpg', content_type = 'image/jpeg')
    images.put_attachment(images[id], image, filename='image', content_type=doc['mime'])
    return score

def removeImage(id):
    '''
    Removes an image from the database.
    '''
    if not id in images:
        raise NoDocument()
    doc = images[id]
    if not 'type' in doc or doc['type'] != 'image':
        raise InvallidType()
    
    docs = []
    for i in doc['tags']:
        t = images[i]
        t['images'].remove(id)
        docs.append(t)
    images.update(docs)
    images.delete(doc)

def addTag(tag, hidden=False):
    '''
    Adds a tag, optionally hidden.
    Returns the created id.
    '''
    if tag in tags():
        raise Exists()
    return images.save({'type': 'tag', 'name': tag, 'hidden': hidden, 'images': []})[0]

def removeTag(tag):
    '''
    Removes a tag.
    '''
    tags = listTags()
    if not tag in tags:
        raise NoDocument()
    tag = tags[tag]
    doc = images[tag]
    for image in tag['images']:
        i = images[image]
        i['tags'].remove(tag)
        print i

def listTags(reverse=False):
    '''
    Returns a list of tags in name indexed order.
    '''
    o = {}
    if not reverse:
        for i in images.view('imagedb/tags'):
            o[i.key] = i.id
    else:
        for i in images.view('imagedb/tags'):
            o[i.id] = i.key
    return o

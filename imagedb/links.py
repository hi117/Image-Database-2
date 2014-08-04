import json
import re
import config

images = config.images

def genLink(type, args, ids):
    '''
    Generates a link for an image.
    type is the type of link
    args are arguments to the generator
    id is a list of image ids to add the created link to
    returns the id of the link created
    '''
    for i in ids:
        if not i in images:
            raise NoDocument()
    if type == 'fileUpload':
        return genLinkFileUpload(ids, args)
    if type == 'danbooru':
        return genLinkDanbooru(ids, args)
    if type == 'simmilar':
        return genLinkSimmilar(ids, args)
    raise InvallidType()

def listSimmilarLinks():
    '''
    Returns a list of document ids for simmilar images.
    '''
    return map(lambda a: a.value, images.view('imagedb/simmilar'))

def genLinkSimmilar(ids, args):
    '''
    Generates a simmilarity link.
    This link is used for images with a low hamming distance.
    '''
    if len(ids) != 2:
        raise KeyError('For a simmilarity link, 2 ids are required')
    doc = {
            'type': 'link',
            'linktype': 'simmilar',
            'images': ids
            }
    id = images.save(doc)[0]
    doc = images[id]
    im = []
    for i in ids:
        image = images[i]
        if not image['type'] == 'image':
            raise InvallidType()
        image['links'].append(id)
        im.append(image)
    images.save(doc)
    images.update(im)
    return id

def genLinkDanbooru(ids, args):
    '''
    Generates a danbooru link.
    This link is used for images from danbooru.
    '''
    if len(ids) != 1:
        raise KeyError('For a danbooru link, only one id may be given')
    doc = args
    doc['type'] = 'link'
    doc['linktype'] = 'danbooru'
    doc['images'] = ids
    image = images[ids[0]]
    if not image['type'] == 'image':
        raise InvallidType()
    id = images.save(doc)[0]
    image['links'].append(id)
    images.save(image)
    return id

def genLinkFileUpload(ids, args):
    '''
    Generates a file upload link
    This link is used if a user uploads the file from their computer
    '''
    if len(ids) != 1:
        raise KeyError('For a file upload, only one id may be given')
    if not 'filename' in args:
        raise KeyError('No Filename Given')
    if not 'mimetype' in args:
        raise KeyError('No Mimetype Given')
    if not 'user' in args:
        raise KeyError('No User Given')
    doc = args
    doc['type'] = 'link'
    doc['linktype'] = 'fileUpload'
    doc['images'] = ids
    image = images[ids[0]]
    if not image['type'] == 'image':
        raise InvallidType()
    id = images.save(doc)[0]
    image['links'].append(id)
    images.save(image)
    return id

def getLink(id):
    '''
    Returns a link.
    '''
    if not id in images:
        raise NoDocument()
    doc = images[id]
    if not ('type' in doc and doc['type'] == 'link'):
        raise InvallidType()

    return doc

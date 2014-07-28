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
    raise InvallidType()

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

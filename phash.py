from PIL import Image
from StringIO import StringIO
import imagehash
import config

def hashToImagehash(h):
    a = []
    for i in re.findall('..', h):
        b = []
        for j in range(8):
            b.append(bool(int('0x' + i, 16) & 2**j))
        a.append(b)
    return imagehash.ImageHash(numpy.array(a, dtype=bool))

def imageHashToInt(h):
    n = 0
    for i in h.hash.flatten():
        n = n*2
        if i:
            n+=1
    return n

def arraySearch(hash, distance, root=-1):
    '''
    Searches the database for a hash.
     * hash: The hash to look for
     * distance: The distance to return values for
    return value:
        A list of all hashes and distances from the input hash in
        {hash: distance, hash: distance, ...} form.
    '''
    pass

def findEntry(hash):
    '''
    Finds the id of the entry a given hash is stored in.
     * hash: The hash to lookup
    return value:
        A document the hash is associated with
    '''
    # Get the index
    index = getIndex()

    id = ''
    n = 9999999
    for i in index:
        if hash > i and hash - i < n:
            id = index[i]
            n = hash - i
    return config.images[id]

def getIndex():
    return config.images.

def arrayInsert(hash, docid):
    '''
    Inserts a hash into the database.
     * hash: the hash to insert
     * docid:  the docid to point to
    return value;
        None
    '''
    pass

def arrayBallance():
    '''
    Ballances the tree, this is an expensive operation.
    '''
    pass

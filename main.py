from flask import *
from PIL import Image
from StringIO import StringIO
import couchdb
import json
import urllib
import tempfile
import imagehash
import subprocess
import re
import numpy

app = Flask(__name__)
app.debug = True

couch = couchdb.Server('http://127.0.0.1:5984')
images = couch['imagedb']

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

@app.route('/')
def index():
    if not 'offset' in request.args:
        return redirect('?offset=0')
    return send_from_directory('./static/', 'index.html')

@app.route('/list')
def list():
    def all(gen, offset, hidden):
        h = hide(gen, hidden)
        n = 0
        for i in h:
            if n / 100 == offset:
                k = i.key
                d = i.value
                i = i.id
                yield '<a href="image/' + i + '"><img src="thumb/' + i + '"></a>' + repr(n) + '\n'
                n+=1
            elif n / 100 > offset:
                break
            else:
                n+=1

    def hide(gen, hidden):
        htags = {}
        for i in images.view('test/hiddenTags'):
            htags[i.key] = i.value
        for i in gen:
            display = True
            for j in i.value['tags']:
                if j in htags and htags[j] not in hidden:
                    display = False
                    break
            if display:
                yield i

    print [request.args]
    if not 'hidden' in request.args:
        return Response(all(images.iterview('imagedb/images', 100), int(request.args['offset']), []))
    else:
        return Response(all(images.iterview('imagedb/images', 100), int(request.args['offset']), map(lambda a: a.encode('utf8'), json.loads(request.args['hidden'].encode('utf8')))))

@app.route('/image/<image>')
def showImage(image):
    if image in images:
        attachment = images[image]['name']
        mime = images[image]['_attachments'][attachment]['content_type']
        for i in range(3):
            try:
                img = images.get_attachment(image, attachment).read()
                break
            except:
                pass
        return Response(img, mimetype=mime)

@app.route('/thumb/<image>')
def showThumb(image):
    if image in images:
        for i in range(3):
            try:
                mime = images[image]['_attachments']['thumbnail.jpg']['content_type']
                return Response(images.get_attachment(image, 'thumbnail.jpg').read(), mimetype=mime)
            except:
                pass
        mime = images[image]['_attachments']['thumbnail.jpg']['content_type']
        return Response(images.get_attachment(image, 'thumbnail.jpg').read(), mimetype=mime)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'GET':
        return send_from_directory('./static/', 'add.html')
    elif request.method == 'POST':
        doc = {'type': 'image', 'links': []}
        # grab all the tags
        tags = {}
        for i in images.view('test/tags'):
            tags[i.key] = i.id
        imTags = []
        for i in json.loads(request.form['tags']):
            if i in tags:
                imTags.append(tags[i])
            else:
                # new tag, need to generate it
                pass
        doc['tags'] = imTags
        # prepare image
        im = request.files['image']
        doc['name'] = im.filename
        im = im.read()
        imp = Image.open(StringIO(im))
        # calculate image hash
        hash = imagehash.phash(imp)
        doc['hash'] = str(hash)
        hashes = images.view('test/hashes')
        for i in hashes:
            if hashToImagehash(i.key) - hash <= 3:
                print i.id
        # generate image thumbnail
        imp.thumbnail((128,128))
        thumb = StringIO()
        imp.convert('RGB').save(thumb, "JPEG")
        # get the exif data and mime
        with tempfile.NamedTemporaryFile() as f:
            f.write(im)
            f.flush()
            exif = json.loads(subprocess.check_output(['exiftool', '-j', f.name]))[0]
            for i in exifIgnore:
                exif.pop(i)
            mime = subprocess.check_output(['file', '--mime-type', f.name]).split(' ')[1]
            doc['exif'] = exif
        print doc

def hashToImagehash(h):
    a = []
    for i in re.findall('..', h):
        b = []
        for j in range(8):
            b.append(bool(int('0x' + i, 16) & 2**j))
        a.append(b)
    return imagehash.ImageHash(numpy.array(a, dtype=bool))

@app.route('/js/<path:path>')
@app.route('/css/<path:path>')
@app.route('/static/<path:path>')
def sStatic(path):
    return send_from_directory('./static/' + str(request.url_rule).split('/')[1], path)

@app.route('/search/')
def sSearch():
    return send_from_directory('./static/', 'search.html')

@app.route('/untagged/')
def untagged():
    return send_from_directory('./static/', 'untagged.html')

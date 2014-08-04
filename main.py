from flask import *
import json
import urllib
import re
import imagedb
import imagedb.links
import config
import os.path

app = Flask(__name__)
app.debug = True

app.secret_key = 'testing'

@app.route('/')
def index():
    if not 'offset' in request.args:
        return redirect('?offset=0')
    return render_template('index.html', images=list(), offset=int(request.args['offset']), username=session['username'] if 'username' in session else None)

def list():
    offset = int(request.args['offset'])
    hidden = request.args['hidden'] if 'hidden' in request.args else []
    def all(gen, offset, hidden):
        h = hide(gen, hidden)
        n = 0
        for i in h:
            if n / 100 == offset:
                k = i.key
                d = i.value
                i = i.id
                yield [i, n]
                n+=1
            elif n / 100 > offset:
                break
            else:
                n+=1

    def hide(gen, hidden):
        for i in imagedb.listTags(hidden=True):
            print i
        htags = map(lambda a: a.id, imagedb.listTags(hidden=True))
        for i in gen:
            display = True
            for j in i.value['tags']:
                if j in htags and j not in hidden:
                    display = False
                    break
            if display:
                yield i

    if not len(hidden):
        return all(imagedb.listImages(), offset, [])
    if 'username' in session:
        return all(imagedb.listImages(), offset, map(lambda a: a.encode('utf8'), json.loads(hidden.encode('utf8'))))
    abort(403)

@app.route('/image/<image>')
def showImage(image):
    if not 'username' in session and imagedb.isHidden(image):
        abort(403)
    i = imagedb.getImage(image, type='image')
    return Response(i[0].read(), mimetype=i[1])

@app.route('/thumb/<image>')
def showThumb(image):
    if not 'username' in session and imagedb.isHidden(image):
        abort(403)
    return Response(imagedb.getImage(image, type='thumb'), mimetype=config.thumbMime)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'GET':
        return render_template('add.html')
    else:
        if 'url' in request.form:
            # if they give a url, we use the url scraper
            return processUrl(request.form['url'])

        if not 'image' in request.files:
            abort(403)
        i = imagedb.addImage(request.files['image'].stream.read())
        print i
        args = {}
        args['filename'] = request.files['image'].filename
        args['mimetype'] = request.files['image'].mimetype
        args['user'] = session['username'] if 'username' in session else 'Anonymous'
        print imagedb.links.genLink('fileUpload', args, [i[0]])
        if len(i[1]) != 0:
            imagedb.mDelete(i[0])
            return render_template('addCollision.html', id=i[0], collisions=i[1])
        return render_template('postAdd.html', id=i[0], pcollisions=i[2], len=len)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        if not 'username' in request.form or not 'password' in request.form:
            abort(401)
        if checkLogin(request.form['username'], request.form['password']):
            session['username'] = request.form['username']
            if 'redirect' in session:
                return redirect(session.pop('redirect'))
            return redirect(url_for('index'))
        else:
            flash('Login failed!')
            return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', 0)
    return redirect(url_for('index'))

@app.route('/get/<id>')
def get(id):
    try:
        doc = imagedb.get(id)
    except imagedb.NoDocument:
        abort(404)
    if not 'type' in doc:
        abort(404)
    if imagedb.isHidden(id) and not 'username' in session:
        abort(403)
    if doc['type'] == 'image':
        return render_template('image.html', doc=doc, getTag=imagedb.getTag, sorted=sorted, username=session['username'] if 'username' in session else None)
    if doc['type'] == 'tag':
        return render_template('tag.html', doc=doc)
    if doc['type'] == 'link' and doc['linktype'] == 'simmilar':
        return render_template('simmilar.html', doc=doc)
    abort(404)

@app.errorhandler(404)
def notFound(e):
    if os.path.isfile('static' + request.path):
        return send_from_directory('static', request.path[1:])
    return render_template('404.html')

@app.errorhandler(403)
def denied(e):
    return render_template('403.html', login=url_for('login'))

def checkLogin(username, password):
    return True

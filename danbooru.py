# -*- coding: utf-8 -*-
import imagedb
import imagedb.links
import requests
import humanfriendly
import time
import sys
import dateutil.parser
from bs4 import BeautifulSoup as bs

s = requests.Session()
tagurl = u'http://danbooru.donmai.us/posts?utf8=✓'
posturl = 'http://danbooru.donmai.us/posts/'
imgurl = 'http://danbooru.donmai.us'

def downloadTag():
    '''
    Downloads a single tag.
    '''
    tag = sys.argv[1]
    offset = int(sys.argv[2]) if len(sys.argv) == 3 else 0
    a = bs(s.get(tagurl + '&tags=' + tag).text)
    # Get total pages
    total = int(str(a.find_all('menu')[-1].find_all('li')[-2].find('a').text))
    for i in range(total-offset):
        downloadPage(tag, i+1+offset)

def downloadPage(tag, page):
    '''
    Downloads a single page.
    '''
    print tagurl + '&page=' + str(page) + '&tags=' + tag
    a = bs(s.get(tagurl + '&page=' + str(page) + '&tags=' + tag).text)
    ids = map(lambda a: a.key, imagedb.images.view('imagedb/danbooruIDs').rows)
    for i in a.find(id='posts').find_all('a'):
        if i.text == '':
            id = i.attrs['href'].split('/')[2].split('?')[0]
            if id in ids:
                continue
            downloadImg(id)

def replaceTag(tag):
    '''
    Tag replacement table.
    '''
    table = {
            'angel beats!': 'Angel Beats',
            'tenshi (angel beats!)': 'Tachibana Kanade',
            'yui (angel beats!)': 'Yui (Angel Beats)',
            'iwasawa': 'Iwasawa Masami',
            'clannad': 'Clannad',
            'rewrite': 'Rewrite',
            'sakagami tomoyo': 'Sakagami Tomoyo',
            'hinata (angel beats!)': 'Hinata (Angel Beats)',
            'kanon': 'Kanon',
            'yuri (angel beats!)': 'Yuri (Angel Beats)',
            }
    if tag in table:
        return table[tag]
    return tag

def downloadImg(img):
    '''
    Downloads a single image.
    '''
    link = {'tags': [], 'pools': [], 'comments': [], 'children': []}
    a = bs(s.get(posturl + img).text)
    tags = []

    # handle tags
    for i in a.find(id='tag-list').find_all('a', {'class':'search-tag'}):
        link['tags'].append(str(i.text))
        tags.append(replaceTag(str(i.text)))
    rating = str(a.find(id='post-information').find_all('li')[6].text.split(' ')[1])
    if rating == 'Questionable':
        tags.append('ecchi')
    elif rating == 'Explicit':
        tags.append('NSFW')

    # get link data
    i = a.find(id='post-information').find_all('li')
    link['id'] = str(i[0].text.split(': ')[1])
    print link['id']
    link['uploader'] = str(i[1].find('a').attrs['href'].split('/')[2])
    link['date'] = time.mktime(dateutil.parser.parse(i[2].find('time').attrs['title']).timetuple())
    if not 'Approver' in i[3].text:
        i = [''] + i
        link['approver'] = ''
    else:
        link['approver'] = str(i[3].find('a').attrs['href'].split('/')[2])
    link['size'] = [humanfriendly.parse_size(i[4].find('a').text), str(i[4].text.split('\n')[2].strip())]
    source = i[5].find('a')
    if source:
        link['source'] = str(source.attrs['href'])
    else:
        link['source'] = ''
    link['rating'] = str(i[6].text.split(': ')[1])
    link['score'] = str(i[7].text.split(': ')[1].strip())
    link['favorites'] = str(i[8].text.split(': ')[1].strip())
    link['status'] = str(i[9].text.split('\n')[6].strip())

    # check for pools
    p = a.find('span', {'class': 'pool-name'})
    if p:
        for i in p.find_all('a'):
            link['pools'].append(str(i.attrs['href'].split('/')[2]))

    # get comments
    for i in a.find('div', {'class': 'list-of-comments'}).find_all('article'):
        comment = {}
        comment['id'] = str(i.attrs['data-comment-id'])
        comment['creator'] = i.attrs['data-creator'].encode('utf8')
        comment['post-id'] = str(i.attrs['data-post-id'])
        comment['score'] = str(i.attrs['data-score'])
        comment['creatorid'] = str(i.find('div', {'class': 'author'}).find('a').attrs['href'].split('/')[2])
        comment['creatorclass'] = str(i.find('div', {'class': 'author'}).find('a').attrs['class'][0])
        comment['comment'] = "".join([str(x) for x in i.find('div', {'class': 'body prose'}).contents])
        link['comments'].append(comment)

    # get children
    p = a.find('div', id='has-children-relationship-preview')
    if p:
        for i in p.find_all('article', {'data-has-children':"false"}):
            if i.attrs['data-parent-id'] == link['id']:
                link['children'].append(str(i.attrs['data-id']))

    # get parent
    p = a.find('div', id='has-parent-relationship-preview')
    if p:
        link['parent'] = str(p.find('article', {'data-id': link['id']}).attrs['data-parent-id'])
    else:
        link['parent'] = ''

    # get the image
    p = a.find('a', id='image-resize-link')
    if p:
        img = str(p.attrs['href'])
    else:
        # if its a video, p will be null
        p = a.find('img', id='image')
        if p:
            img = str(p.attrs['src'])
        else:
            return

    print imgurl + img
    image = s.get(imgurl + img).content
    
    try:
        doc = imagedb.addImage(image)
    except:
        print 'failed!'
        return
    print doc
    # if there is a collision, add the danbooru link to it and tag the image
    if len(doc[1]) != 0:
        imagedb.mDelete(doc[0])
        id = doc[1][0]
    else:
        id = doc[0]
        for i in doc[2]:
            imagedb.links.genLinkSimmilar([id, i], {})
    l = imagedb.links.genLinkDanbooru([id], link)
    print l
    for i in tags:
        imagedb.addToTag(id, i)

downloadTag()

import couchdb

couch = couchdb.Server('http://127.0.0.1:5984')
images = couch['imagedbtest']

thumbsize = (128, 128)

defaultTag = 'needs tag'

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

thumbMime = 'image/jpeg'

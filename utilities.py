from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.ext import blobstore


class FileClass(ndb.Model):
    name = ndb.StringProperty()
    blob = ndb.BlobKeyProperty()


class DirectoryClass(ndb.Model):
    name = ndb.StringProperty()
    path = ndb.StringProperty()
    parent = ndb.KeyProperty()
    directories = ndb.KeyProperty(repeated=True)
    files = ndb.KeyProperty(repeated=True)


class UserClass(ndb.Model):
    root = ndb.KeyProperty()
    current = ndb.KeyProperty()
    email = ndb.StringProperty()

    @staticmethod
    def get(user_id):
        return ndb.Key(UserClass, user_id).get()


class Errorhandler(ndb.Model):
    error = ndb.StringProperty()


class Share(ndb.Model):
    folder = ndb.KeyProperty()
    permission = ndb.StringProperty()
    user = ndb.KeyProperty()
    blob = ndb.BlobKeyProperty()

    @staticmethod
    def ancestor_query():
        return Share.query(ancestor=ndb.Key(Share, 'Share'))



def getUser():
    user = users.get_current_user()
    if user:
        userKey = ndb.Key(UserClass, user.user_id())
        return userKey.get()


def addUser(user):
    user = UserClass(id=user.user_id(), email=user.email())

    directory = DirectoryClass(id=user.key.id() + '/')
    directory.parent = None
    directory.name = 'root'
    directory.path = '/'
    directory.put()

    user.root = directory.key
    user.put()

    user.current = ndb.Key(DirectoryClass, user.key.id() + '/')
    user.put()
    put_error("")

def getFileObject(file_name):
    return ndb.Key(FileClass, getUser().key.id() + getPath(file_name, getUser().current.get())).get()


def getPath(name, parentObject):
    if isRoot():
        return parentObject.path + name
    else:
        return parentObject.path + '/' + name


def isRoot():
    return True if getUser().current.get().parent is None else False


def addDirectory(name, parentKey):
    parentObject = parentKey.get()
    path = getPath(name, parentObject)
    directory = DirectoryClass(id=getUser().key.id() + path)

    if directory.key not in parentObject.directories:
        parentObject.directories.append(directory.key)
        parentObject.put()
        directory.parent = parentKey
        directory.name = name
        directory.path = path
        directory.put()


def addFile(upload, fileName):
    currentObject = getUser().current.get()
    fileId = getUser().key.id() + getPath(fileName, currentObject)
    fileKey = ndb.Key(FileClass, fileId)


    fileObject = FileClass(id=fileId)
    fileObject.name = fileName
    fileObject.blob = upload.key()
    fileObject.put()

    currentObject.files.append(fileKey)
    currentObject.put()




def deleteDirectory(directoryName):
    parentObject = getUser().current.get()
    directoryKey = ndb.Key(DirectoryClass, getUser().key.id() + getPath(directoryName, parentObject))
    directoryObject = directoryKey.get()

    if not directoryObject.files and not directoryObject.directories :
        parentObject.directories.remove(directoryKey)
        parentObject.put()
        directoryKey.delete()
    else:
        put_error("Directory Not Empty")


def deleteFile(fileName):
    parentObject = getUser().current.get()
    fileKey = ndb.Key(FileClass, getUser().key.id() + getPath(fileName, parentObject))
    parentObject.files.remove(fileKey)
    parentObject.put()
    blobstore.delete(fileKey.get().blob)
    fileKey.delete()


def up():
    user = getUser()
    if not isRoot():
        user.current = getUser().current.get().parent
        user.put()
    put_error("")

def home():
    user = getUser()
    user.current = ndb.Key(DirectoryClass, user.key.id() + '/')
    user.put()
    put_error("")

def navigateDirectory(directoryName):
    user = getUser()
    directoryId = user.key.id() + getPath(directoryName, getUser().current.get())
    user.current = ndb.Key(DirectoryClass, directoryId)
    user.put()
    put_error("")

def duplicates(ele):
    dupes = list()
    duplicates = list()

    for i in range(len(ele)):
        if (ele.count(ele[i]) > 1 ):
            dupes.append(ele[i])
            duplicates = set(dupes)

    return duplicates

def put_error(msg):
    my_user = getUser()
    error_id = my_user.key.id()+"Error"
    errorhandler = Errorhandler(id=error_id)
    errorhandler.error = msg
    errorhandler.put()

def get_error():
    my_user = getUser()

    error_id = my_user.key.id()+"Error"
    error_key = ndb.Key(Errorhandler, error_id)
    error = error_key.get().error
    return error


def getduplicatefilesfromDropbox():
    fileList = list()
    pathslist = list()
    dirlist = list()
    returnedval1 = list()
    returnedval2 = list()
    newfilelist = list()
    newpathslist = list()
    user = getUser()
    query = DirectoryClass.query(ancestor=ndb.Key(DirectoryClass, user.key.id(
    ) + '/')).filter(DirectoryClass.name == "root", DirectoryClass.path == "/")
    filenames = [c.files for c in query]
    dirnames = [c.directories for c in query]
    for filekeys in filenames:
        for files in filekeys:
            fileList.append(files.get().name)
            pathslist.append("/")
    for dirkeys in dirnames:
        for dirs in dirkeys:
            dirlist.append(dirs.get().name)
    returnedval1, returnedval2 = duplicateFilesAppender(
        dirlist, "/", fileList, pathslist)

    for i in range(len(returnedval1)):
        if (returnedval1.count(returnedval1[i]) > 1):
            newfilelist.append(returnedval1[i])
            newpathslist.append(returnedval2[i])

    return newfilelist, newpathslist


def duplicateFilesAppender(dirlist, parentPath, fileList, pathslist):
    new = list()
    dirobj = list()
    user = getUser()

    for names in dirlist:
        path = parentPath + names
        query = DirectoryClass.query(ancestor=ndb.Key(DirectoryClass, user.key.id(
        ) + path)).filter(DirectoryClass.name == names, DirectoryClass.path == path)
        filenames = [c.files for c in query]
        dirnames = [c.directories for c in query]
        for filekeys in filenames:
            for files in filekeys:
                fileList.append(files.get().name)
                pathslist.append(path)
        for dirkeys in dirnames:
            for dirs in dirkeys:
                dirobj.append(dirs.get().name)
        duplicateFilesAppender(dirobj, path, fileList, pathslist)

    return fileList, pathslist




def shareFile(emailUser, fileName):
    guest = UserClass.query(UserClass.email == emailUser).get()
    fileDetails = FileClass.query(FileClass.name == fileName).get()
    parentObject = getUser().current.get()
    fileKey = ndb.Key(UserClass, users.get_current_user().user_id(), FileClass, getUser().key.id() + getPath(fileName,
                                                                                                             parentObject))
    if guest:
        Share(
            parent=ndb.Key(Share, 'Share'),
            folder=fileKey,
            user=guest.key,
            permission=u'rw',
            blob=fileDetails.blob
        ).put()
    else:
        put_error("user doesn't exist")


def sharedFileHandler(upload, fileName):
    currentObject = getUser().current.get()
    fileId = getUser().key.id() + getPath(fileName, currentObject)
    fileKey = ndb.Key(FileClass, fileId)

    if fileKey not in currentObject.files:
        fileObject = FileClass(id=fileId)
        fileObject.name = fileName
        fileObject.blob = upload.blob
        fileObject.put()

        currentObject.files.append(fileKey)
        currentObject.put()

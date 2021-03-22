from webapp2 import WSGIApplication, RequestHandler
from google.appengine.ext import blobstore
from google.appengine.api import users
from google.appengine.ext.webapp import blobstore_handlers
import jinja2
import os
import re
from utilities import *

jinjaEnv = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
                              extensions=['jinja2.ext.autoescape'], autoescape=True)


class download(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self):
        try:
            filename = self.request.get('file_name')
            self.send_blob(getFileObject(filename).blob)
            self.response.headers['Content-Disposition'] = str(filename)
        except Exception as e:
            print(e)
            self.error(404)


class upload(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        try:
            uploadingFiles = self.get_uploads()
            for file in uploadingFiles:
                addFile(file, blobstore.BlobInfo(file.key()).filename)
        except Exception as e:
            print(e)
        self.redirect('/')


class main(RequestHandler):

    def get(self):
        self.response.headers['Content-Type'] = 'text/html'

        if users.get_current_user():
            if not getUser():
                addUser(users.get_current_user())

            if self.request.get('directory_name') != '':
                navigateDirectory(self.request.get('directory_name'))
                self.redirect('/')

            sortedDir = sorted(getUser().current.get().directories,
                               key=lambda element: element.get().name.lower())
            directories_in_current_path = [
                element.get().name for element in sortedDir]

            sortedFiles = sorted(getUser().current.get().files, key=lambda element: element.
                                 get().name.lower())
            files_in_current_path = [
                element.get().name for element in sortedFiles]

            error = get_error()

            duplicate_files_in_current_path = duplicates(files_in_current_path)

            first,second = getduplicatefilesfromDropbox()
            result = [list(a) for a in zip(first, second)]

            myuser = UserClass.get(users.get_current_user().user_id())
            for share in Share.ancestor_query().filter(Share.user == myuser.key).fetch():
                if share.blob:
                    files_in_current_path.append(share.folder.id().split('/')[1])
                    sharedFileHandler(share, blobstore.BlobInfo(share.blob).filename)

            kwargs = {
                'url': users.create_logout_url(self.request.uri),
                'user': users.get_current_user(),
                'directories': directories_in_current_path,
                'files': files_in_current_path,
                'current_path': getUser().current.get().path,
                'is_not_in_root': not isRoot(),
                'upload_url': blobstore.create_upload_url('/upload'),
                'error': error,
                'duplicates': duplicate_files_in_current_path,
                'dropboxduplicates' : result
            }

            self.response.write(jinjaEnv.get_template(
                '/templates/main.html').render(kwargs))

        else:
            kwargs = {
                'url': users.create_login_url(self.request.uri)
            }
            self.response.write(jinjaEnv.get_template(
                '/templates/login.html').render(kwargs))

    def post(self):
        self.response.headers['Content-Type'] = 'text/html'
        button = self.request.get('button')

        if button == 'Add':
            directory_name = re.sub(
                r'[/;]', '', self.request.get('value')).lstrip()
            if not (directory_name is None or directory_name == ''):
                addDirectory(directory_name, getUser().current)

        elif button == 'Delete':
            kind = self.request.get('kind')
            if kind == 'file':
                deleteFile(self.request.get('name'))
            elif kind == 'directory':
                deleteDirectory(self.request.get('name'))

        elif button == 'Up':
            up()

        elif button == 'Home':
            home()

        elif button == 'Share':
            shareFile(str(self.request.get('email').strip()), str(self.request.get('name')))

        self.redirect('/')


app = WSGIApplication(
    [('/', main), ('/upload', upload), ('/download', download)])

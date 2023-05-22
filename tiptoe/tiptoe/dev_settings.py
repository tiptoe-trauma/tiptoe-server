from tiptoe.settings import *

print("Running on DEV settings")


ALLOWED_HOSTS = ['localhost',
                 '127.0.0.1',
                 '[::1]']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tiptoe',
        'USER': 'postgres', 
        'PASSWORD': 'password123',
        'HOST': 'database',
        'PORT': '5432',
    }
}
#EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
#EMAIL_FILE_PATH = '/Users/whortonjustinm/work/email'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_FILE_PATH = ''
EMAIL_HOST = 'mail.uams.edu'
EMAIL_PORT = 25

TRIPLESTORE_URL = 'http://triplestore:7200'  + '/repositories/tiptoe'
TRIPLESTORE_USER = 'blank' 
TRIPLESTORE_PASSWORD = 'blank'

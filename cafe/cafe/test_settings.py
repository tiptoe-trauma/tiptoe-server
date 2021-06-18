from cafe.settings import *

print("Running on DEV settings")


ALLOWED_HOSTS = ['localhost',
                 '127.0.0.1',
                 '[::1]']

DATABASES = {
     'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'test.sqlite3'),
    }
}
EMAIL_HOST = 'example.com'
EMAIL_HOST_USER = 'bad'
EMAIL_HOST_PASSWORD = 'bad'

TRIPLESTORE_URL = 'http://localhost:7200'

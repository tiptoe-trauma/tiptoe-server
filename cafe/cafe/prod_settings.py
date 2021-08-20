from cafe.settings import *

print("Running on PROD settings")

ALLOWED_HOSTS = ['0.0.0.0', 'django-cafe-dev-jmw.apps.dbmi.cloud', 'cafe-trauma.com']

SECRET_KEY = os.getenv('CAFE_DJANGO_SECRET_KEY', '^%(#2k$5n08-i2=t8f%w3iy3^)g(=nfjy#%)!!rqx_0q3e#*ym')

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'cafe',
        'USER': os.getenv('CAFE_DATABASE_USER', 'mydatabaseuser'),
        'PASSWORD': os.getenv('CAFE_DATABASE_PASSWORD', 'mypassword'),
        'HOST': os.getenv('CAFE_DATABASE_HOST', 'localhost'),
        'PORT': '5432',
    }
}

EMAIL_HOST = 'mail.uams.edu'
EMAIL_PORT = 25

TRIPLESTORE_URL = os.getenv('CAFE_TRIPLESTORE_URL', 'http://triplestore-cafe.apps.dbmi.cloud/repositories/cafe')
STATIC_ROOT = '/var/www/html/static'

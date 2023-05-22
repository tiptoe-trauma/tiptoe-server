from tiptoe.settings import *

print("Running on PROD settings")

ALLOWED_HOSTS = ['0.0.0.0', 'django-tiptoe-dev-jmw.apps.dbmi.cloud', 'cafe-trauma.com', 'cafedb.ad.uams.edu']
LOGIN_URL = 'tiptoe.apps.dbmi.cloud'

SECRET_KEY = os.getenv('TIPTOE_DJANGO_SECRET_KEY', '^%(#2k$5n08-i2=t8f%w3iy3^)g(=nfjy#%)!!rqx_0q3e#*ym')

DEBUG = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tiptoe',
        'USER': os.getenv('TIPTOE_DATABASE_USER', 'mydatabaseuser'),
        'PASSWORD': os.getenv('TIPTOE_DATABASE_PASSWORD', 'mypassword'),
        'HOST': os.getenv('TIPTOE_DATABASE_HOST', 'localhost'),
        'PORT': '5432',
    }
}

EMAIL_HOST = 'mail.uams.edu'
EMAIL_PORT = 25

TRIPLESTORE_URL = os.getenv('TIPTOE_TRIPLESTORE_URL', 'https://triplestore-tiptoe.apps.dbmi.cloud') + '/repositories/tiptoe'
TRIPLESTORE_USER = os.getenv('TIPTOE_TRIPLESTORE_USER', 'blank')
TRIPLESTORE_PASSWORD = os.getenv('TIPTOE_TRIPLESTORE_PASSWORD', 'blank')
STATIC_ROOT = '/var/www/html/static'

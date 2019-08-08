# cafe-server

This is a [Django](https://www.djangoproject.com/) application so installation or use instructions will mostly come from their documentation.

The short version and some project specific things are.
* Clone the repo
* (optionally) Create a python3 virtualenv and activate it
* `pip install -r requirements.txt`
* Update `cafe/cafe/settings.py`
* `export SECRET_KEY=something_secret_here`
* `./manage syncdb`
* `./manage createsuperuser`
* `./manage runserver`

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

You must edit the email config file in `cafe/cafe`. The file is called `email_config.cfg.example`. Edit the file to use your username and password and then rename it to `email_config.cfg`. Be sure not to push your account information.
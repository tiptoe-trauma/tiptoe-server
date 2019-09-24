The major change with the move to Heroku is that the django app server is now responsible for serving all fo the static content for the site. Most importantly this includes the production compiled cafe-app angular codebase. To enable this the WhiteNoise middleware layer was added. In addition certain heroku environment variables are fed into email and various other settings.

If CAFE needs to be transitioned back to a traditional server environment the settings file located at this commit is probably a good place to start. https://github.com/cafe-trauma/cafe-server/blob/31ab9bedf7e1b42fc06b51f88b7b4bff23be4feb/cafe/cafe/settings.py

To continue development in the Heroku style any changes to the angular app needs to be compiled and moved over to the cafe/angular directory before being pushed to heroku. Mathias owns the Heroku account the app is hosted from so a new developer should be able to easily link their development environment to it using the `heroku remote:add -a cafe-trauma` command.

The app should be largely stable and should only need to have its library versions upgraded for security reasons. It currently has the domain http://app.cafe-trauma.com pointed to it.

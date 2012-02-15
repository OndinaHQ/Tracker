
# Tracker

A basic issue tracking system

# Running tracker

To run a local server, type `python3 tracker.py --run` after creating
and editing your settings.ini and configuring couchdb and Amazon S3.

Please keep in mind that the public release of tracker is very alpha
indeed. The OpenID login has a few glitches, and not all of Tracker's
features work outside of Ondina yet. Thank you for being brave.

To deploy using mod_wsgi (python3), add see an example configuration
at `wsgi.markdown`.


## Files and Directories

### Files

 - server.py
   Glue code to get the built-in CherryPy webserver going, cp configuration

 - settings.ini
   Settings that should not be written into code

 - db.passwd
   The database password. This file can live anywhere on the filesystem,
   it's path is set it in settings.ini - use $PWD/ to reference the apps
   directory, next to server.py

   You have to create this file before running the app. It's content is
   the plain text password for CouchDB - it will not be hashed automatically
   and you should therefore select a more-or-less secure location. Please
   note that the password is sent to CouchDB in the clear, therefore
   **CouchDB MUST run on the local host** and couchdb's config must set
   the `bind_address` parameter.

 - s3.passwd
   Similar to db.passwd, this file contains your S3 access key and secret,
   separated by a colon. The S3 plugin will not work properly if this file
   isn't provided, but Tracker will still run.


### MVC Webapp Directories

 - models/
   Classes abstracting bug-tracking functionality

 - views/
   HTML Templates (mako)

 - controller/
   Classes implementing the application server

 - static/
   HTML dependencies, such as jQuery

 - assets/
   HTML deppendencies such as stylesheets and scripts

### Modules

 - cherrypy/
   a static copy of CherryPy, in case it's not installed

 - openid2rp/
   implements OpenID 2.0 as a relying party
   ATTENTION: This is modified (heavily) - do not upgrade from upstream

 - markupsafe/
   escape for html, slightly better than what python ships

 - markdown/
   Gruber's Markdown
   ATTENTION: this is modified (slightly) - do not upgrade from upstream

 - couchdb/
   The simplest possible database adaptor for CouchDB

 - mako/
   a static copy of Mako Templates, in case it's not installed



Copying and distribution of this file, with or without modification,
are permitted in any medium without royalty provided the copyright
notice and this notice are preserved.  This file is offered as-is,
without any warranty.

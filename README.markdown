
# Tracker

An Issue tracking system

## Running tracker
Please keep in mind that the public release of tracker is very alpha
indeed. The OpenID login has a few glitches, and not all of Tracker's
features work outside of Ondina yet. Thank you for being brave.

In order to get started with tracker, you will need:

 - An apache server running mod_wsgi for Python 3000 (for testing,
   you can also use the built-in cherrypy http server using "--run")
 - A CouchDB server, with http basic auth enabled, running
   on localhost (and only listening on 127.0.0.1)
 - An Amazon S3 account (optional, but recommended)
 - A good amount of adventurousness :)

## Dependencies

  - Python >= 3.2
  - CouchDB
  - Amazon S3

## Packages

 - CherryPy
 - Mako Templates
 - OpenID2RP
 - Markupsafe
 - Python Markdown

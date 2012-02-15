#    Copyright (C) 2012  Stefano Palazzo <stefano.palazzo@gmail.com>
#    Copyright (C) 2012  Ondina, LLC. <http://ondina.co>

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import cherrypy
import mako.lookup
import openid2rp
import markupsafe
import sys
import json
import configparser
import atexit

from controller import tracker


wd = os.path.split(os.path.realpath(__file__))[0]

class Application (tracker.Application):

    class Static (object):

        pass


    class Assets (object):

        pass


    static, assets = Static(), Assets()
    view = mako.lookup.TemplateLookup(directories=[os.path.join(
        wd, "views")], input_encoding="utf8").get_template


if "--run" not in sys.argv:
    print("WARNING")
    print("if you meant to run this as a standalone server,")
    print("provide the \"--run\" argument. Otherwise this is")
    print("the wsgi entry point")
    application = Application()
    if not os.path.exists("/tmp/tracker-sessions"):
        os.mkdir("/tmp/tracker-sessions")
    cherrypy.tree.mount(application, script_name="/", config=
        os.path.join(wd, "settings.ini"))
    cherrypy.config.update({"error_page.default": application.error_default})
    def application(environ, start_response):
        return cherrypy.tree(environ, start_response)


if __name__ == '__main__':
    if "--run" in sys.argv:
        application = Application()
        if not os.path.exists("/tmp/tracker-sessions"):
            os.mkdir("/tmp/tracker-sessions")
        cherrypy.config.update({"error_page.default": application.error_default})
        cherrypy.quickstart(application, config=os.path.join(
            wd, "settings.ini"))

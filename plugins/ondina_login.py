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

import cherrypy
import json
import urllib.request
import urllib.parse


def try_verify(session_id, host="cp.ondina.co",
        return_host="tracker.ondina.co", fail=False):
    ''' internal ondina authentication via the control panel '''
    if not session_id:
        if fail:
            raise cherrypy.HTTPError(401)
        raise cherrypy.HTTPRedirect("http://{}/user/login".format(host) +
            "?redirect=http://{}".format(return_host))
    request = urllib.request.Request(url="http://{}/api/login".format(host),
        data=urllib.parse.urlencode({"key": "session_id",
        "session_id": session_id}).encode(), headers={
        "Server": "TrackerHTTPClient/0.0"})
    try:
        r = urllib.request.urlopen(request)
        user = json.loads(r.read().decode())
        r.close()
        return user
    except Exception as e:
        pass
    if fail:
        raise cherrypy.HTTPError(401)
    raise cherrypy.HTTPRedirect("http://{}/user/login".format(host) +
        "?redirect=http://{}".format(return_host))

def get_user(user_id, host="cp.ondina.co"):
    request = urllib.request.Request(url="http://{}/api/login".format(host),
        data=urllib.parse.urlencode({"key": "id",
        "id": user_id}).encode(), headers={
        "Server": "TrackerHTTPClient/0.0"})
    r = urllib.request.urlopen(request)
    user = json.loads(r.read().decode())
    r.close()
    return user

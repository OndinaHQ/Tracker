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

import json
import base64
import http.client
import urllib.parse
import functools
import cherrypy


class DatabaseConnection (object):

    def __init__(self, user, passwd, server="127.0.0.1:5984"):
        self.uri = urllib.parse.urlparse("http://" + server).netloc
        self.auth = ({'Authorization': "Basic " +
            base64.b64encode(user.encode() + b":" + passwd.encode()).decode()}
            if user and passwd is not None else {})
        cherrypy.log.error("Initializing netloc: {}".format(
            self.uri), severity=20, context="COUCHDB")
        self.cache = {}

    def request(self, method, action, headers=None, body=None, cache=True):
        cache_key = json.dumps((method, action, headers, body))
        if cache == False and cache_key in self.cache:
            del self.cache[cache_key]
        cherrypy.log.error("Database request: {} {}".format(
            method, action), severity=20, context="COUCHDB")
        headers, body = headers or {}, body or {}
        headers.update(self.auth)
        if cache_key in self.cache and self.cache[cache_key]["Etag"]:
            headers.update({"If-None-Match": self.cache[cache_key]["Etag"]})
        headers.update({'Content-Type': 'application/json'})
        connection = http.client.HTTPConnection(self.uri)
        connection.request(method, action, json.dumps(body), headers)
        response = connection.getresponse()
        if response.status == 304:
            return self.cache[cache_key]["response"]
        try:
            response.object = json.loads(response.read().decode())
        except Exception as e:
            raise type(e)(response.status, *e.args)
        if cache_key not in self.cache:
            self.cache[cache_key] = {}
        self.cache[cache_key]["Etag"] = dict(response.getheaders()).get("Etag")
        self.cache[cache_key]["response"] = response.object
        return response.object

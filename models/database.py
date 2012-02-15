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
import math
import json
import urllib.parse

import couchdb.couch


class DatabaseAbstraction (object):

    def __init__(self, user, passwd, server="127.0.0.1:5984"):
        self.conn = couchdb.couch.DatabaseConnection(user, passwd, server)
        self.__check_and_create_db("tracker", die=True)
        if "error" in (self.conn.request("GET", "/tracker/_design/issues/"
                "_view/index")):
            cherrypy.log.error("'_design/issues/' does not"
                " exist - I will create it", severity=89, context="COUCHDB")
            self._add_views("issues", {
                "index": {"map":
                    "function(doc) {\n  emit(-doc.date, {\"id\": "
                        "doc._id, \"tags\": doc.tags, \"owner\": doc.owner});\n}"},
                "get_page": {"map":
                    "function(doc) {\n  emit(-doc.date, doc);\n}"},
            })

    def __check_and_create_db(self, name, first_try=True, die=True, reason=""):
        if name not in self.conn.request("GET", "/_all_dbs"):
            cherrypy.log.error(("Database '{}' does not exist!{}").format(
                    name, (" I'm going to create it." if first_try else
                    " I will not try to create it again.")),
                severity=89, context="COUCHDB")
            if first_try:
                reason = self.conn.request("PUT", "/" + name)
                self.__check_and_create_db(name, False, reason=reason)
            else:
                cherrypy.log.error(("Fatal: could not create"
                    " the database '{}'{}").format(name,
                    " ({})".format(reason) if reason else ""),
                    severity=100, context="COUCHDB")
                if die:
                    exit(1)
        else:
            cherrypy.log.error("Database '{}' exists.".format(name),
                severity=20, context="COUCHDB")

    def get_id(self):
        r = self.view("issues", "index", limit=1)
        r = (int(r["rows"][0]["id"].split("-")[1]) + 1) if r["rows"] else 1
        return r

    def post(self, document):
        id_ = "issue-" + str(self.get_id())
        response = self.conn.request("PUT", "/tracker/" + id_, body=document)
        cherrypy.log.error("PUT document returned {}".format({"ok":
            response.get("ok")}), severity=20, context="COUCHDB")
        return id_

    def get_all_tags(self):
        issues = [i["value"]["tags"] for i in (self.index().get("rows") or [])]
        all_tags = set()
        for tags in issues:
            all_tags |= set(tags)
        return list(all_tags)

    def get(self, i, **kwargs):
        _id = "issue-" + str(i)
        return self.conn.request("GET", "/tracker/" + _id + "?" +
            urllib.parse.urlencode({k: json.dumps(v)
            for k, v in kwargs.items()}))

    def put(self, i, document):
        _id = "issue-" + str(i)
        return self.conn.request("PUT", "/tracker/" + _id, body=document)

    def view(self, design, view, **args):
        qs = urllib.parse.urlencode({k: json.dumps(v)
            for k, v in args.items()})
        return self.conn.request("GET", "/tracker/_design/{}"
            "/_view/{}?{}".format(design, view, qs), cache=False)

    def index(self, **args):
        return self.view("issues", "index", **args)

    def get_page(self, page, pagesize):
        keys = [i["id"] for i in self.index()["rows"]]
        page_keys = keys[(page * pagesize) - pagesize:][:pagesize]
        rows = self.conn.request("POST", "/tracker/_all_docs"
            "?include_docs=true", body={"keys": page_keys})["rows"]
        return {
            "pages": int(math.ceil(len(keys) / pagesize)),
            "page": page, "pagesize": pagesize, "rows": rows,
        }

    def get_page_by_tag(self, tag, page, pagesize):
        keys = [i["id"] for i in self.by_tag(tag)["rows"]]
        page_keys = keys[(page * pagesize) - pagesize:][:pagesize]
        rows = self.conn.request("POST", "/tracker/_all_docs"
            "?include_docs=true", body={"keys": page_keys})["rows"]
        return {
            "pages": int(math.ceil(len(keys) / pagesize)),
            "page": page, "pagesize": pagesize, "rows": rows,
            "total": len(keys),
        }

    def get_page_by_user(self, user, page, pagesize):
        keys = [i["id"] for i in self.by_user(user)["rows"]]
        page_keys = keys[(page * pagesize) - pagesize:][:pagesize]
        rows = self.conn.request("POST", "/tracker/_all_docs"
            "?include_docs=true", body={"keys": page_keys})["rows"]
        return {
            "pages": int(math.ceil(len(keys) / pagesize)),
            "page": page, "pagesize": pagesize, "rows": rows,
            "total": len(keys),
        }

    def by_tag(self, tag):
        issues = self.index()
        if "rows" in issues:
            issues["rows"] = [i for i in issues["rows"]
                if tag in i["value"]["tags"]]
        return issues

    def by_user(self, user):
        issues = self.index()
        if "rows" in issues:
            issues["rows"] = [i for i in issues["rows"]
                if i["value"].get("owner") == user]
        return issues

    def _add_views(self, design, views):
        self.conn.request("PUT", "/tracker/_design/{}/".format(design), body={
                '_id': "_design/" + design,
                'language': 'javascript',
                "views": views,
            })

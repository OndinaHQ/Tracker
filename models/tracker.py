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
import cherrypy
import functools


class Tracker (object):

    def __init__(self, database):
        self.database = database

    def new_issue(self, issue):
        _id = self.database.post(issue)
        return _id

    def mark_user_affected(self, issue, user, u):
        doc = self.database.get(issue)
        self.check_permission(doc["owner"], u, True)
        doc["affects"] = list(set(doc["affects"] + [user]))
        self.database.put(issue, doc)

    def mark_user_not_affected(self, issue, user, u):
        doc = self.database.get(issue)
        self.check_permission(doc["owner"], u, True)
        doc["affects"] = list(set(doc["affects"]) ^ {user})
        self.database.put(issue, doc)

    def update_issue(self, issue, new_doc, user):
        doc = self.database.get(issue)
        self.check_permission(doc["owner"], user, True)
        doc.update(new_doc)
        doc["edit_count"] = (doc.get("edit_count") or 0) + 1
        self.database.put(issue, doc)

    def mark_dupe(self, issue, dupe, user):
        doc = self.database.get(issue)
        self.check_permission(doc["owner"], user, False)
        doc["dupes"] = list(set(doc["dupes"] + [dupe]))
        self.database.put(issue, doc)

    def mark_delete(self, issue, user):
        doc = self.database.get(issue)
        self.check_permission(doc["owner"], user, True)
        doc["deleted"] = True
        self.database.put(issue, doc)

    def mark_undelete(self, issue, user):
        doc = self.database.get(issue)
        self.check_permission(doc["owner"], user, True)
        doc["deleted"] = False
        self.database.put(issue, doc)

    @functools.lru_cache(400)
    def get_issue_title(self, issue):
        if issue is not None:
            doc = self.database.get(issue)
            return doc.get("title")

    def change_status(self, issue, status, user):
        doc = self.database.get(issue)
        self.check_permission(doc["owner"], user, False)
        doc["status"] = status
        self.database.put(issue, doc)

    def check_permission(self, owner, user, owners=False):
        if owners and int(owner) == (user["id"]):
            return True
        if user.get("is_admin"):
            return True
        raise cherrypy.HTTPError(400, "Bad Request")

    def comment(self, issue, comment):
        doc = self.database.get(issue)
        doc["comments"].append(comment)
        self.database.put(issue, doc)



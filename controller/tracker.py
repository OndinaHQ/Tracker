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
import openid2rp

import ast
import configparser
import os.path
import json
import time
import binascii
import functools
import urllib.parse
import threading
import io
import hmac
import hashlib
import uuid

import markdown
import markupsafe

from models import tracker
from models import database
from plugins import ondina_login
from plugins import mail
from plugins import s3
import lib.fuzzy_time


class ApplicationAPI (object):

    def __init__(self, parent, api_secret):
        self.parent, self.__secret = parent, api_secret

    @cherrypy.expose
    def index(self, tag="", page="1", pagesize="10", key="", callback="", _=""):
        ''' return issues as json - this is a jsonp method if callback is provided '''
        self.parent.do_auth(fail=True)
        if not self.validate(key):
            return self.unauthorized()
        try:
            page, pagesize = int(page), int(pagesize)
        except ValueError:
            cherrypy.response.status = 400
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps({"error": "malformed page and/or pagesize"},
                indent=4).encode()
        try:
            c_tag = urllib.parse.unquote_plus(tag)
        except (UnicodeDecodeError, binascii.Error):
            cherrypy.response.status = 400
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps({"error": "malformed tag"}, indent=4).encode()
        if not c_tag.strip():
            response = self.parent.database.get_page(int(page), int(pagesize))
        else:
            response = self.parent.database.get_page_by_tag(c_tag,
                int(page), int(pagesize))
            response.update({"tag": tag.strip()})
            response.update({"user_id": (cherrypy.session.get("user")
                or {}).get("id")})
        cherrypy.response.headers["Content-Type"] = "application/json"
        if callback:
            return (callback.encode() + b"(" + json.dumps(response,
                indent=4).encode() + b")")
        return json.dumps(response, indent=4).encode()


    @cherrypy.expose
    def issue(self, title="", description="", tags="", hidden="",
            user_id="", key=""):
        '''
        Usage Example:

            POST /api/issue HTTP/1.1
            Host: tracker.ondina-staging.local
            Content-Length: 72
            Content-Type: application/x-www-form-urlencoded

            tags=a,b&title=test&description=testing+api&user_id=2&key=your_key

        Response:

            {"result": "issue-38"}

        '''
        self.parent.do_auth(fail=True)
        if not self.validate(key):
            return self.unauthorized()
        if cherrypy.request.method != "POST":
            cherrypy.response.status = 404
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps({"error": "method not allowed"}).encode()
        tags = markupsafe.escape(tags)
        tags = list(set(tags.replace(",", " ").split()))
        if hidden:
            tags.append("hidden-issue")
        if len(tags) == 0:
            tags.append("untagged")
        issue = {
            "title": markupsafe.escape(title),
            "description": description,
            "tags": tags,
            "date": time.time(),
            "score": 0,
            "deleted": False,
            "edit_count": 0,
            "browser": None,
            "status": "new",
            "owner": int(user_id),
            "comments": [],
            "dupes": [],
            "affects": [int(user_id), ]
        }
        issue_text_html = markdown.markdown(issue["description"],
            safe_mode="escape")
        _id = self.parent.tracker.new_issue(issue)
        threading.Thread(target=mail.tracker_alert, args=(
            issue, issue_text_html, title, _id,
            cherrypy.session.get("user"))).start()
        cherrypy.response.headers["Content-Type"] = "application/json"
        return json.dumps({"result": _id}).encode()

    def validate(self, key):
        return key == self.__secret

    def unauthorized(self):
        cherrypy.response.status = 401
        cherrypy.response.headers["Content-Type"] = "application/json"
        return json.dumps({"error": "unauthorized"}, indent=4).encode()

class Application (object):

    def __init__(self):
        wd = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]
        self.config = configparser.ConfigParser()
        self.config.read(os.path.join(wd, "settings.ini"))
        self.database = database.DatabaseAbstraction(
            user=ast.literal_eval(self.config["couchdb"]["username"].strip()),
            passwd=open(ast.literal_eval(self.config["couchdb"]["password"]
                ).replace("$PWD", wd)).read().strip(),
            server=ast.literal_eval(self.config["couchdb"]["host"].strip()))
        self.tracker = tracker.Tracker(self.database)
        self.max_page_size = 20
        if "web" in self.config and "max_page_size" in self.config["web"]:
            self.max_page_size = int(ast.literal_eval(
                self.config["web"]["max_page_size"].strip()))
        self.default_page_size = 4
        if "web" in self.config and "default_page_size" in self.config["web"]:
            self.default_page_size = int(ast.literal_eval(
                self.config["web"]["default_page_size"].strip()))
        for i in ("access_file", "error_file"):
            if "global" in self.config and "log." + i in self.config["global"]:
                d = self.config["global"]["log." + i]
                d = os.path.split(ast.literal_eval(d))[0]
                if not os.path.exists(d):
                    os.mkdir(d)
        self.authentication_method = 'ondina'
        if "web" in self.config and "authentication" in self.config["web"]:
            self.authentication_method = ast.literal_eval(
                self.config["web"]["authentication"].strip())


        self.x_tracker_host = 'tracker.ondina.co'
        if "web" in self.config and "x_tracker_host" in self.config["web"]:
            self.x_tracker_host = ast.literal_eval(
                self.config["web"]["x_tracker_host"].strip())

        self.x_control_panel_host = 'cp.ondina.co'
        if "web" in self.config and "x_control_panel_host" in self.config["web"]:
            self.x_control_panel_host = ast.literal_eval(
                self.config["web"]["x_control_panel_host"].strip())

        self.wd = wd
        cherrypy.log.error("Completely relaxed.", severity=20,
            context="COUCHDB")

        api_secret = "null"
        if "api" in self.config and "secret" in self.config["api"]:
            api_secret = ast.literal_eval(
                self.config["api"]["secret"].strip())
        self.api = ApplicationAPI(self, api_secret)
        self.s3_enabled = True
        try:
            s3data = open(ast.literal_eval(self.config["s3"]["data"]
                    ).replace("$PWD", wd)).read().strip()
            self.s3 = s3.S3(*s3data.strip().split(":"))
        except IOError:
            cherrypy.log.error("Amazon S3 support is disabled!",
                severity=70, context="AWS")
            self.s3_enabled = False

        self.example_user = {"id": "0", "email":
            "example@gmail.com", "password": None,
            "first_name": "Example", "last_name": "User",
            "default_account": "example", "is_admin": True,
            "account": "example"}

    @cherrypy.expose
    def new_issue(self, title="", description="", tags="", browser="",
            hidden=False, redirect=""):
        if cherrypy.request.headers.get("X-Do-Not-Track") == 1:
            browser = ""
        self.do_auth()
        #if cherrypy.request.method != "POST":
        #    raise cherrypy.HTTPRedirect("/new")
        tags = markupsafe.escape(tags)
        tags = list(set(tags.replace(",", " ").split()))
        if hidden:
            tags.append("hidden-issue")
        if len(tags) == 0:
            tags.append("untagged")
        issue = {
            "title": markupsafe.escape(title),
            "description": description,
            "tags": tags,
            "date": time.time(),
            "score": 0,
            "deleted": False,
            "edit_count": 0,
            "browser": browser,
            "status": "new",
            "owner": cherrypy.session["user"]["id"],
            "comments": [],  # TODO
            "dupes": [],  # TODO
            "affects": [int(cherrypy.session["user"]["id"]), ]}
        issue_text_html = markdown.markdown(issue["description"],
            safe_mode="escape")
        _id = self.tracker.new_issue(issue)
        threading.Thread(target=mail.tracker_alert, args=(
            issue, issue_text_html, title, _id,
            cherrypy.session.get("user"))).start()
        if redirect:
            raise cherrypy.HTTPRedirect(redirect)
        raise cherrypy.HTTPRedirect("/issue/" + _id.split("-")[1])

    @cherrypy.expose
    def page(self, page="1", pagesize=..., asjson="", **kwargs):
        self.do_auth()
        if pagesize == ...:
            pagesize = self.default_page_size
        if page == "1":
            raise cherrypy.HTTPRedirect("/")
        try:
            page, pagesize = int(page), int(pagesize)
        except:
            raise cherrypy.HTTPError(404, "Not Found")
        if int(pagesize) > self.max_page_size:
            pagesize = self.max_page_size
        issues = self.database.get_page(int(page), int(pagesize))
        if len(issues["rows"]) == 0 and page != 1:
            raise cherrypy.HTTPError(404, "Not Found")
        if asjson.lower() in ("asjson", "true", ):
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps(issues, indent=4).encode()
        return self.view("index.html").render(auth=self.is_authenticated,
            page="/", issues=issues, **self.get_default_args())

    @cherrypy.expose
    def index(self, **args):
        self.do_auth()
        return self.page(page=1, **args)

    @cherrypy.expose
    def tags(self, tag="", _="", page="1", pagesize=..., asjson=""):
        self.do_auth()
        if pagesize == ...:
            pagesize = self.default_page_size
        if tag == "" and asjson.lower() in ("asjson", "true", ):
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps(self.database.get_all_tags(), indent=4).encode()
        if tag == "":
            raise cherrypy.HTTPError(404, "Not Found")
        try:
            c_tag = urllib.parse.unquote_plus(tag)
        except (UnicodeDecodeError, binascii.Error):
            raise cherrypy.HTTPError(404, "Not Found")
        if int(pagesize) > self.max_page_size:
            pagesize = self.max_page_size
        issues = self.database.get_page_by_tag(c_tag, int(page), int(pagesize))
        if len(issues["rows"]) == 0:
            raise cherrypy.HTTPError(404, "Not Found")
        if asjson.lower() in ("asjson", "true", ):
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps(issues, indent=4).encode()
        return self.view("index.html").render(auth=self.is_authenticated,
            page="/tags", c_tag=c_tag, tag_id=tag,
            issues=issues, **self.get_default_args())

    @cherrypy.expose
    def users(self, user="", _="", page="1", pagesize=..., asjson=""):
        self.do_auth()
        if int(user) != cherrypy.session["user"]["id"]:
            if not (cherrypy.session.get("user") or {}).get("is_admin"):
                raise cherrypy.HTTPError(404)
        if pagesize == ...:
            pagesize = self.default_page_size
        if user == "":
            raise cherrypy.HTTPError(404, "Not Found")
        if int(pagesize) > self.max_page_size:
            pagesize = self.max_page_size
        issues = self.database.get_page_by_user(user, int(page), int(pagesize))
        if len(issues["rows"]) == 0:
            if self.authentication_method == "ondina":
                raise cherrypy.HTTPError(404, "Not Found")
        name = self.get_user(user)["first_name"] + " " + self.get_user(user)["last_name"]
        me = user == cherrypy.session["user"]["id"]
        if asjson.lower() in ("asjson", "true", ):
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps(issues, indent=4).encode()
        return self.view("index.html").render(auth=self.is_authenticated,
            page="/users", issues=issues, name=name, user_id=user, me=me,
            **self.get_default_args())

    @cherrypy.expose
    def issue(self, _id="", _="", asjson=""):
        self.do_auth()
        if not _id:
            raise cherrypy.HTTPRedirect("/")
        issue = self.database.get(_id)
        if issue.get("reason") == "missing":
            raise cherrypy.HTTPError(404, "Not Found")
        if asjson.lower() in ("asjson", "true", ):
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps(issue, indent=4).encode()
        else:
            return self.view("issue.html").render(issue=issue,
                page="/issue", issue_text_html=markdown.markdown(
                    issue["description"], safe_mode="escape"),
                **self.get_default_args())

    @cherrypy.expose
    def new(self, tags="", title="", description=""):
        self.do_auth()
        return self.view("new.html").render(page="/new",
            prefill={"tags": tags or None, "title": title or None,
                "description": description or None},
            **self.get_default_args())

    @cherrypy.expose
    def introduction(self):
        self.do_auth()
        return self.view("introduction.html").render(page="/introduction",
            **self.get_default_args())

    @cherrypy.expose
    def mark_affects(self, issue=""):
        self.do_auth()
        if cherrypy.request.method != "POST":
            raise cherrypy.HTTPError(401, "Method Not Allowed")
        self.tracker.mark_user_affected(issue.split("-")[1],
            int(cherrypy.session["user"]["id"]), cherrypy.session["user"])
        return "okay..."

    @cherrypy.expose
    def mark_womm(self, issue=""):
        self.do_auth()
        if cherrypy.request.method != "POST":
            raise cherrypy.HTTPError(401, "Method Not Allowed")
        self.tracker.mark_user_not_affected(issue.split("-")[1],
            int(cherrypy.session["user"]["id"]), cherrypy.session["user"])
        return "okay..."

    @cherrypy.expose
    def mark_dupe(self, issue="", dupe=""):
        dupe = dupe.strip()
        try:
            dupe_id = int(dupe)
        except ValueError:
            try:
                dupe_id = int([i for i in
                    urllib.parse.urlsplit(dupe).path.split("/")
                    if all(j in "0123456789" for j in i) and i][0])
            except:
                cherrypy.session["error"] = "dupe_id"
                raise cherrypy.HTTPRedirect("/issue/" + issue.split("-")[1])
        dupe = "/issue/" + str(dupe_id)
        self.do_auth()
        if cherrypy.request.method != "POST":
            raise cherrypy.HTTPError(401, "Method Not Allowed")
        self.tracker.mark_dupe(issue.split("-")[1], dupe, cherrypy.session["user"])
        raise cherrypy.HTTPRedirect("/issue/" + issue.split("-")[1])

    @cherrypy.expose
    def mark_delete(self, issue=""):
        self.do_auth()
        if cherrypy.request.method != "POST":
            raise cherrypy.HTTPError(401, "Method Not Allowed")
        self.tracker.mark_delete(issue.split("-")[1], cherrypy.session["user"])
        if cherrypy.session["user"].get("is_admin"):
            raise cherrypy.HTTPRedirect("/issue/" + issue.split("-")[1])
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def mark_undelete(self, issue=""):
        self.do_auth()
        if cherrypy.request.method != "POST":
            raise cherrypy.HTTPError(401, "Method Not Allowed")
        self.tracker.mark_undelete(issue.split("-")[1], cherrypy.session["user"])
        if cherrypy.session["user"].get("is_admin"):
            raise cherrypy.HTTPRedirect("/issue/" + issue.split("-")[1])
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def change_status(self, status="", issue=""):
        self.do_auth()
        if cherrypy.request.method != "POST":
            raise cherrypy.HTTPError(401, "Method Not Allowed")
        self.tracker.change_status(issue.split("-")[1], status, cherrypy.session["user"])
        if cherrypy.session["user"].get("is_admin"):
            raise cherrypy.HTTPRedirect("/issue/" + issue.split("-")[1])
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def update_issue(self, issue, title="", description="", tags="", hidden=False):
        self.do_auth()
        if cherrypy.request.method != "POST":
            raise cherrypy.HTTPRedirect("/new")
        tags = markupsafe.escape(tags)
        tags = list(set(tags.replace(",", " ").split()))
        if hidden:
            tags.append("hidden-issue")
        if len(tags) == 0:
            tags.append("untagged")
        self.tracker.update_issue(issue.split("-")[1], {
            "title": markupsafe.escape(title),
            "description": description,
            "tags": tags,
            "update": time.time(),
        }, cherrypy.session["user"])
        raise cherrypy.HTTPRedirect("/issue/" + issue.split("-")[1])

    @cherrypy.expose
    def comment(self, issue="", comment=""):
        self.do_auth()
        self.tracker.comment(issue.split("-")[1], {
            "user": cherrypy.session["user"]["id"],
            "comment": comment,
            "date": time.time(),
        })
        raise cherrypy.HTTPRedirect("/issue/" + issue.split("-")[1])

    @cherrypy.expose
    def login(self, provider="", **q):
        if not q and not provider:
            return self.view("login.html").render(page="/login",
                **self.get_default_args())
        auth = openid2rp.cp_login(q, provider)
        user_id = hashlib.sha1(auth["openid.identity"].encode()).hexdigest()
        user_id = int(user_id, 16)
        cherrypy.session["user"] = {"last_name": "", "first_name":
            openid2rp.name(auth), "email": openid2rp.email(auth),
            "is_admin": False, "id": user_id}
        raise cherrypy.HTTPRedirect("/")

    def do_auth(self, fail=False):
        if not self.is_authenticated():
            if self.authentication_method == "ondina":
                try:
                    cp_login_session_id = cherrypy.request.cookie[
                        "ondina_session"].value
                except KeyError:
                    cp_login_session_id = None
                user = ondina_login.try_verify(cp_login_session_id,
                    self.x_control_panel_host, self.x_tracker_host, fail)
                cherrypy.session["user"] = user
            elif self.authentication_method == "null":
                cherrypy.session["user"] = self.example_user
            elif self.authentication_method == "openid":
                if not cherrypy.session.get("user"):
                    raise cherrypy.HTTPRedirect("/login")
                raise cherrypy.HTTPRedirect("/")
            else:
                raise cherrypy.HTTPError(500)

    @functools.lru_cache(80)  # TODO
    def get_user(self, user_id):
        if self.authentication_method == "ondina":
            return ondina_login.get_user(user_id,
                self.x_control_panel_host)
        elif self.authentication_method == "null":
            return self.example_user
        else:
            return cherrypy.session["user"]

    @cherrypy.expose
    def img_upload(self, image=None, csrf_token=None):
        if cherrypy.request.method == "GET":
            self.do_auth() # this looks like some serious crypto, but it doesn't *really* help!
            cherrypy.session["upload-token"] = t = uuid.uuid4().hex
            return self.view("upload.html").render(csrf_token=t)
        if cherrypy.request.method != "POST":
            cherrypy.response.status = 405
            cherrypy.response.headers["Content-Type"] = "text/plain"
            return b"405"
        try:
            valid_content_types = ("image/gif", "image/jpeg", "image/jpg",
                "image/pjpeg", "image/png", ) # jpg is nonstandard
            self.do_auth()
            user_id = (cherrypy.session.get("user") or {}).get("id")
            if user_id is None:
                cherrypy.response.status = 401
                cherrypy.response.headers["Content-Type"] = "text/plain"
                return b"401"
            if csrf_token is None or csrf_token != cherrypy.session.get("upload-token"):
                cherrypy.response.status = 401
                cherrypy.response.headers["Content-Type"] = "text/plain"
                return b"401"
            if image is None or image.file is None:
                cherrypy.response.status = 404
                cherrypy.response.headers["Content-Type"] = "text/plain"
                return b"404"
            size, data = 0, io.BytesIO()
            for _ in range((1024 * 1024 * 2) // 8192):
                c = image.file.read(8192)
                if not c:
                    break
                data.write(c)
            else:
                cherrypy.response.status = 413
                cherrypy.response.headers["Content-Type"] = "text/plain"
                return b"413"
            if str(image.content_type) not in valid_content_types:
                cherrypy.response.status = 415
                cherrypy.response.headers["Content-Type"] = "text/plain"
                return b"415"
            filename = user_id + "_" + uuid.uuid4().hex + str(image.filename)
            url = self.s3.upload("ondina-tracker", data.getvalue(),
                str(image.content_type), filename)
            cherrypy.response.headers["Content-Type"] = "application/json"
            return json.dumps(url).encode()
        except Exception as e:
            raise  # TODO
            cherrypy.response.status = 500
            cherrypy.response.headers["Content-Type"] = "text/plain"
            return b"500"

    def do_deauth(self):
        pass#cherrypy.lib.sessions.expire()

    def is_authenticated(self):
        return (cherrypy.session.get("user") or {}).get("id") is not None

    def escape_link(self, s):
         return ''.join(i if i in "abcdefghijklmnopqrstuvwxyz.-"
            "0123456_" else "-"
            for i in s.lower())

    def date_delta(self, date):
        st = time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(date))
        dt = lib.fuzzy_time.fuzzy_delta(time.time(), date)
        return st, dt

    @functools.lru_cache(-1)
    def have_issues(self, u):
        if u is not None:
            return self.database.get_page_by_user(u, 1, 1)["total"]

    def get_base_url(self):
        url = urllib.parse.urlsplit(cherrypy.url())
        return url.scheme + "://" + url.netloc

    def get_issue_title(self, issue_id):
        try:
            issue_id = int(str(issue_id).split("-")[-1].split("/")[-1])
        except ValueError:
            issue_id = None
        try:
            return self.tracker.get_issue_title(issue_id)
        except Exception as e:
            return repr(e)

    def get_default_args(self, **q):
        return {
            "session": dict(cherrypy.session),
            "escape_link": self.escape_link,
            "escape": markupsafe.escape,
            "have_issues": self.have_issues(
                (cherrypy.session.get("user") or {}).get("id")),
            "uquote": urllib.parse.quote_plus,
            "get_user": self.get_user,
            "date_delta": self.date_delta,
            "user": cherrypy.session.get("user"),
            "base_url": self.get_base_url(),
            "url": cherrypy.url(),
            "invisible_tags": ("invisible-tag", ),
            "s_error": cherrypy.session.pop("error", None),
            "get_title": self.get_issue_title,
            "s3_enabled": self.s3_enabled,
        }

    @cherrypy.expose
    def robots_txt(self):
        try:
            cherrypy.response.headers["Content-Type"] = "text/plain"
            return open(os.path.join(self.wd, "static", "robots.txt")).read()
        except IOError:
            raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def humans_txt(self):
        try:
            cherrypy.response.headers["Content-Type"] = "text/plain"
            return open(os.path.join(self.wd, "static", "humans.txt")).read()
        except IOError:
            raise cherrypy.HTTPError(404)

    @cherrypy.expose
    def favicon_ico(self):
        try:
            cherrypy.response.headers["Content-Type"] = "image/x-icon"
            return open(os.path.join(self.wd, "static",
                "favicon.ico"), "rb").read()
        except IOError:
            raise cherrypy.HTTPError(404)

    def error_default(self, status, message, traceback, version):
        return self.view("error.html").render(status=status, message=message,
            traceback=traceback, version=version, page="error")

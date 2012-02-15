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
import markupsafe

from email.header import Header
from email.message import Message
from email.charset import Charset
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import smtplib
import os.path
import html.parser
import urllib.parse


def unescape(s):
    return html.parser.HTMLParser().unescape(s)

def send(fromaddr, toaddr, subject, message, smtp="localhost:25",
        username=None, password=None, tls=False):
    s = smtplib.SMTP(smtp)
    try:
        if tls:
            s.ehlo()
            s.starttls()
        s.ehlo()
        if username is not None and password is not None:
            s.login(username, password)
        s.sendmail(fromaddr, toaddr, message.as_string().encode())
    finally:
        s.quit()

def tracker_alert(issue, html_body, title, _id, user):
    wd = os.path.split(os.path.realpath(__file__))[0]
    url = ("http://tracker.ondina.co/issue/" + _id.split("-")[1])
    message = MIMEMultipart('alternative')
    message['Subject'] = subj = "Tracker Alert: New Issue ({})".format(
        _id.split("-")[1])
    message['From'] = "Ondina Tracker <no-reply@ondina.co>"
    message['To'] = "Tracker Alert <tracker-alert@ondina.co>"
    text = open(os.path.join(wd, "mail.txt")).read()
    html = open(os.path.join(wd, "mail.html")).read()
    html = html.replace("{{{title}}}", title).replace("{{{body}}}",
        html_body).replace("{{{link}}}", "http://tracker.ondina.co/"
        "issue/{}".format(_id.split("-")[1]))
    text = text.replace("{{{title}}}", title).replace("{{{link}}}",
        "http://tracker.ondina.co/issue/{}".format(_id.split("-")[1]))
    text_message = MIMEText(text, 'plain', "UTF-8")
    html_message = MIMEText(html, 'html', "UTF-8")
    message.attach(text_message)
    message.attach(html_message)
    send("Ondina Tracker <no-reply@ondina.co>",
        "Tracker Alert <tracker-alert@ondina.co>",
        subj, message)

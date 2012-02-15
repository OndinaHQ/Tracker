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

import time
import hmac
import hashlib
import http.client
import urllib.parse
import base64
import collections

class S3Error (Exception):

    def __init__(self, status, response):
        self.status, self.response = status, response

    def __str__(self):
        return "{}: {}".format(self.status, self.response)

    def __str__(self):
        return "S3Error({}, {})".format(repr(self.status), repr(self.response))


class S3 (object):
    '''
    Usage:

    >>> s3 = S3(YOUR_ACCESS_KEY_ID, YOUR_SECRET_ACCESS_KEY)
    >>> s3.upload("some-bucket", open("image.png", "rb").read(),
        "image/png", "image3838838.png")
    https://s3.amazonaws.com/some-bucket/image3838838.png


    '''

    def __init__(self, access_key, secret_key):
        self.__access_key, self.__secret_key = access_key, secret_key

    def __request(self, method, bucket, host, action, body, content_type, fn):
        date = time.strftime("%c GMT", time.gmtime())
        headers = collections.OrderedDict((
            ("x-amz-acl", "public-read"),
            ("Content-Type", content_type),
            ("Content-Length", len(body)),
            ("Host", bucket + "." + host),
            ("Date", date), 
        ))
        string_to_sign = (method + "\n" +
            "\n" +
            content_type + "\n" +
            date + "\n" +
            "x-amz-acl:public-read\n" + 
            "/" + bucket + "/" + fn)
        signature = base64.b64encode(hmac.new(self.__secret_key.encode(),
            string_to_sign.encode(), hashlib.sha1).digest()).decode()
        authorization = "AWS " + self.__access_key + ":" + signature
        headers.update({"Authorization": authorization})
        connection = http.client.HTTPSConnection(bucket + "." + host)
        action = action + "?" + urllib.parse.urlencode({})  
        connection.request(method, action, body, headers)
        response = connection.getresponse()
        if response.status != 200:
            raise S3Error(response.status, response.read())
        return "https://s3.amazonaws.com/{}/{}".format(bucket, fn)

    def upload(self, bucket, data, content_type, filename):
        return self.__request("PUT", bucket, "s3.amazonaws.com", "/" +
            filename, data, content_type, filename)

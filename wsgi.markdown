Example configuration for apache with py3-mod-wsgi:

       <VirtualHost *:80>
                ServerAdmin tracker@example.com
                ServerName tracker.ondina-staging.local
                ServerAlias tracker.ondina-staging.local
                DocumentRoot /home/stefano/tracker/
                WSGIDaemonProcess tracker.ondina-staging.local user=stefano group=stefano home=/home/stefano/ python-path=/home/stefano/tracker umask=0022 processes=2 threads=15 maximum-requests=500
                WSGIProcessGroup tracker.ondina-staging.local
                WSGIScriptAlias	/ /home/stefano/tracker/server.py
                <Directory /home/stefano/tracker>
                    Options Indexes FollowSymLinks MultiViews
                    AllowOverride all
                    Order deny,allow
                    Allow from all
                </Directory>

                ErrorLog /home/stefano/tracker/error.log
                LogLevel warn
                CustomLog /home/stefano/tracker/access.log combined
        </VirtualHost>


Copying and distribution of this file, with or without modification,
are permitted in any medium without royalty provided the copyright
notice and this notice are preserved.  This file is offered as-is,
without any warranty.

# This file is part of LazyLibrarian.
#
# LazyLibrarian is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LazyLibrarian is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LazyLibrarian.  If not, see <http://www.gnu.org/licenses/>.

import smtplib
from email.utils import formatdate, formataddr
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

import lazylibrarian
import os
from lazylibrarian import logger, database
from lazylibrarian.common import notifyStrings, NOTIFY_SNATCH, NOTIFY_DOWNLOAD
from lazylibrarian.formatter import check_int


class EmailNotifier:
    def __init__(self):
        pass

    @staticmethod
    def _notify(message, event, force=False, files=None):

        # suppress notifications if the notifier is disabled but the notify options are checked
        if not lazylibrarian.CONFIG['USE_EMAIL'] and not force:
            return False

        subject = event
        text = message

        logger.debug('Email notification: %s' % message['Subject'])
        logger.debug('Email from: %s' % message['From'])
        logger.debug('Email to: %s' % message['To'])
        logger.debug('Email text: %s' % text)
        logger.debug('Files: %s' % files)

        if files:
            message = MIMEMultipart()
            message.attach(MIMEText(text))
        else:
            message = MIMEText(text, 'plain', "utf-8")

        message['Subject'] = subject
        message['From'] = formataddr(('LazyLibrarian', lazylibrarian.CONFIG['EMAIL_FROM']))
        message['To'] = lazylibrarian.CONFIG['EMAIL_TO']
        message['Date'] = formatdate(localtime=True)

        if files:
            for f in files:
                if os.path.getsize(f) > 20000000:
                    message.attach(MIMEText('%s is too large to email' % os.path.basename(f)))
                else:
                    with open(f, "rb") as fil:
                        part = MIMEApplication(fil.read(), Name=os.path.basename(f))
                        part['Content-Disposition'] = 'attachment; filename="%s"' % os.path.basename(f)
                        message.attach(part)

        try:
            if lazylibrarian.CONFIG['EMAIL_SSL']:
                mailserver = smtplib.SMTP_SSL(lazylibrarian.CONFIG['EMAIL_SMTP_SERVER'],
                                              check_int(lazylibrarian.CONFIG['EMAIL_SMTP_PORT'], 465))
            else:
                mailserver = smtplib.SMTP(lazylibrarian.CONFIG['EMAIL_SMTP_SERVER'],
                                          check_int(lazylibrarian.CONFIG['EMAIL_SMTP_PORT'], 25))

            if lazylibrarian.CONFIG['EMAIL_TLS']:
                mailserver.starttls()
            else:
                mailserver.ehlo()

            if lazylibrarian.CONFIG['EMAIL_SMTP_USER']:
                mailserver.login(lazylibrarian.CONFIG['EMAIL_SMTP_USER'], lazylibrarian.CONFIG['EMAIL_SMTP_PASSWORD'])

            mailserver.sendmail(lazylibrarian.CONFIG['EMAIL_FROM'], lazylibrarian.CONFIG['EMAIL_TO'],
                                message.as_string())
            mailserver.quit()
            return True

        except Exception as e:
            logger.warn('Error sending Email: %s' % e)
            return False

            #
            # Public functions
            #

    def notify_snatch(self, title):
        if lazylibrarian.CONFIG['EMAIL_NOTIFY_ONSNATCH']:
            return self._notify(message=title, event=notifyStrings[NOTIFY_SNATCH])

    def notify_download(self, title, bookid=None, force=False):
        if lazylibrarian.CONFIG['EMAIL_NOTIFY_ONDOWNLOAD']:
            filename = ''
            files = None
            event=notifyStrings[NOTIFY_DOWNLOAD]
            if bookid:
                myDB = database.DBConnection()
                data = myDB.match('SELECT BookFile,BookName from books where BookID=?', (bookid,))
                try:
                    filename = data['BookFile']
                    title = data['BookName']
                except Exception:
                    data = myDB.match('SELECT IssueFile,Title,IssueDate from magazines where BookID=?', (bookid,))
                    try:
                        filename = data['IssueFile']
                        title = "%s - %s" % (data['Title'], data['IssueDate'])
                    except Exception:
                        filename = ''
                if filename:
                    files = [filename]  # could add cover_image, opf
                    event = "LazyLibrarian Download"
            return self._notify(message=title, event=event, force=force, files=files)

    def test_notify(self, title='Test'):
        message = u"This is a test notification from LazyLibrarian"
        if lazylibrarian.CONFIG['EMAIL_SENDFILE_ONDOWNLOAD']:
            myDB = database.DBConnection()
            data = myDB.match('SELECT bookid from books where bookfile <> ""')
            if data:
                return self.notify_download(title=message, bookid=data['bookid'], force=True)

        return self._notify(message=message, event=title, force=True)

notifier = EmailNotifier

"""
ErrorMailer extension sends an email when a spider encounters an error.
Code is based on the StatsMailer extension

Use ERRORMAILER_RCPTS setting to enable and give the recipient mail address
"""

from scrapy import signals
from scrapy.mail import MailSender
from scrapy.exceptions import NotConfigured
from django.utils.timezone import utc

class ErrorMailer(object):

    def __init__(self, stats, recipients, mail):
        self.stats = stats
        self.recipients = recipients
        self.mail = mail

    @classmethod
    def from_crawler(cls, crawler):
        recipients = crawler.settings.getlist("ERRORMAILER_RCPTS")
        if not recipients:
            raise NotConfigured
        mail = MailSender.from_settings(crawler.settings)
        o = cls(crawler.stats, recipients, mail)
        crawler.signals.connect(o.spider_closed, signal=signals.spider_closed)
        #crawler.signals.connect(o.spider_error, signal=signals.spider_closed)
        #crawler.signals.connect(o.response_received, signal=signals.response_received)
        return o
    
    def spider_closed(self, spider):
        spider_stats = self.stats.get_stats(spider)
        
        body = ""
        error = False
        if 'finished' != spider_stats['finish_reason']:
            body += "Finish Reason: %s\n" % spider_stats['finish_reason']
            error = True
            
        for key, value in spider_stats.iteritems(): 
            if (key.startswith('downloader/response_status_count/') and 
                'downloader/response_status_count/200' != key and
                'downloader/response_status_count/302' != key):
                body += "%s: %s\n" % (key, value)
                error = True
            if (key.startswith('spider_exceptions')):
                body += "%s: %s\n" % (key, value)
                error = True
            if (key.startswith('downloader/exception_type_count')):
                body += "%s: %s\n" % (key, value)
                error = True
            if ('log_count/ERROR' == key or
                'log_count/CRITICAL' == key):
                body += "%s: %s\n" % (key, value)
                error = True
            
        if not spider_stats.get('downloader/request_count', 0):
            body += "No requests processed\n"
            error = True
            
        if not spider_stats.get('downloader/response_count', 0):
            body += "No responses processed\n"
            error = True
        
        if error:
            return self.mail.send(self.recipients, "%s spider ERROR" % spider.name, body)
        

        
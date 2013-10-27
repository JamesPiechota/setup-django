import os
from {{scrapy_project}}.settings import USER_AGENT_LIST
import random
from scrapy import log
import urllib
 
class RandomUserAgentMiddleware(object):
# Source: http://snipplr.com/view/66992/
 
    def process_request(self, request, spider):
        ua  = random.choice(USER_AGENT_LIST)
        if ua:
            request.headers.setdefault('User-Agent', ua)

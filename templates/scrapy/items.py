# This is an example Item from https://github.com/scrapy/dirbot
# It is referenced by the sample dmoz.py spider

from scrapy.item import Item, Field

class Website(Item):

    name = Field()
    description = Field()
    url = Field()
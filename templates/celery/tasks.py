import logging
import os
import time
import importlib

from celery import Celery, chain, task, group
from celery.task import periodic_task
from celery.schedules import crontab
from datetime import timedelta

from twisted.internet import reactor

from scrapy.crawler import Crawler
from scrapy.settings import CrawlerSettings
from scrapy import log, signals
from {{scrapy_project}}.spiders.dmoz import DmozSpider

celery = Celery('tasks')
celery.config_from_object('{{project}}.settings')

scrapy_settings_module = importlib.import_module('{{scrapy_project}}.settings')


@task
def crawl(spider_class):
    log.start()
    spider = spider_class()
    crawler = Crawler(CrawlerSettings(scrapy_settings_module))
    crawler.signals.connect(reactor.stop, signal=signals.spider_closed)
    crawler.configure()
    crawler.crawl(spider)
    crawler.start()
    reactor.run()
    
@task()
def add(x, y):
    return x + y
    
@task()
def do_it():
    chain(crawl.si(DmozSpider),
          add.si(1,5),
          ).apply_async()

#do_it.si().apply_async()
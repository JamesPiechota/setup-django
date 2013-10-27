#!/usr/bin/env python
import tempfile
import subprocess
import os
import re
import random


class ShellScript(object):
    
    def __init__(self, log_file):
        self._log_file = "%s/%s" % (os.getcwd(), log_file)
        os.remove(self._log_file)
        f = open(self._log_file, 'w')
        f.close()
        
        self._temp_dir = tempfile.mkdtemp()
        self._script = tempfile.NamedTemporaryFile(dir=self._temp_dir, suffix = ".sh", delete=False)
        self._src_dir = os.path.dirname(os.path.realpath(__file__))
        print self._temp_dir
        print self._script.name
        
    def add(self, command, redirect=True):
        self._script.write("echo %s\n" % (command))
        if redirect:
            self._script.write("%s >> %s\n" % (command, self._log_file))
        else:
            self._script.write("%s\n" % command)
            
    def add_section(self, comment):
        self._script.write("\n###############################################################################\n")
        self._script.write("# " + comment)
        self._script.write("\n################################################################################\n")
        
    def add_commit(self, message):
        self.add("git add .")
        self.add("git commit -a -m '%s'" % message)
        
    def add_template(self, template, dst_dir, replace={}):
        filename = os.path.basename(template)
        src_path = "%s/templates/%s" % (self._src_dir, template)
        temp_path = "%s/%s" % (self._temp_dir, template)
        dst_path = "%s/%s" % (dst_dir, filename)
        subprocess.call("mkdir -p %s" % os.path.dirname(temp_path), shell=True)
        if replace:
            src = open(src_path, 'r')
            dst = open(temp_path, 'w')
            for line in src:
                new_line = line
                matches = re.findall("{{\s*(\w+)\s*}}", new_line)
                for match in matches:
                    new_line = re.sub("{{\s*%s\s*}}" % match, replace[match], new_line)
                dst.write(new_line)
            src.close()
            dst.close()
        else:
            subprocess.call("cp -f %s %s" % (src_path, temp_path), shell=True)
        self.add("mkdir -p %s" % os.path.dirname(dst_path))
        self.add("cp -f %s %s" % (temp_path, dst_path))
        
    def run(self):
        self._script.close()
        #subprocess.call("cat %s" % self._script.name, shell=True)
        subprocess.call("/bin/sh %s" % self._script.name, shell=True)

def setup_virtualenv(script, config):
    script.add_section("Create and activate a virtualenv")
    script.add("source `which virtualenvwrapper.sh`")
    script.add("mkvirtualenv %s" % config["project"])
        
def install_packages(script, config):
    script.add_section("Install all necessary python packages")
    script.add("pip install django")
    script.add("pip install psycopg2")
    script.add("pip install south")
    script.add("pip install django-crispy-forms")
    script.add("pip install dj-database-url")
    script.add("pip install django-celery")
    script.add("pip install Scrapy")
    script.add("pip install -U celery-with-redis")
        
def initialize_project(script, config):
    script.add_section("Create django project and local git repo")

    script.add("django-admin.py startproject %s" % config['project'])
    script.add("cd %s" % config['project'])
    script.add("git init")
    script.add_commit("Initial commit of %s" % config['project'])
    script.add_template("django/settings.py", config["project"])
    script.add_template("django/wsgi.py", config["project"], replace=config)
    script.add("pip freeze > requirements.txt")
    script.add_commit("Install default settings.py, wsgi.py, and requirements.txt")
    
def create_database(script, config):
    script.add_section("Create database")
    script.add("psql -c \"create user %s with password '%s'\"" % (config["db_user"], config["local_db_password"]))
    script.add("psql -c 'create database %s'" % config["project"])
    script.add("psql -c 'grant all privileges on database %s to %s'" % (config["project"], config["db_user"]))
    
def set_environment(script, config):
    script.add_template("virtualenv/postactivate", "$VIRTUAL_ENV/bin", replace=config)
    script.add("workon %s" % config["project"])
    
def initialize_south(script, config):
    script.add_section("Initialize South") 
    script.add("python manage.py syncdb", redirect=False)
    script.add("git add .")
    script.add("git commit -a -m 'Added South for database migrations'")
    
def initialize_scrapy(script, config):
    script.add_section("Initialize scrapy")
    script.add("scrapy startproject %s" % config["scrapy_project"])
    script.add("mv %s xxx%s" % (config["scrapy_project"], config["scrapy_project"]))
    script.add("mv xxx%s/* ." % config["scrapy_project"])
    script.add("rmdir xxx%s" % config["scrapy_project"])
    script.add_template("scrapy/settings.py", "scrape", replace=config)
    script.add_template("scrapy/extensions.py", "scrape", replace=config)
    script.add_template("scrapy/middleware.py", "scrape", replace=config)
    script.add_template("scrapy/items.py", "scrape", replace=config)
    script.add_template("scrapy/dmoz.py", "scrape/spiders", replace=config)
    
def initialize_celery(script, config):
    script.add_section("Initialize Celery") 
    script.add("brew install redis")
    script.add("python manage.py migrate djcelery")
    script.add_template("celery/tasks.py", ".", replace=config)
    
    
if __name__ == '__main__':
    script = ShellScript("setup.log")
    
    print "This script assumes you have a psql server installed and running"
    print "Type 'redis-server &' to run the installed redis server"
    
    config = {}
    config["project"] = "blockboard"
    config["db_user"] = "blockboard"
    config["local_db_password"] = "local1"
    config["heroku_db_password"] = "local1"
    config["mandrill_user"] = "james@nyle.co"
    config["mandrill_password"] = "5m1v3p2Y1Kzoivi_FF16dQ"
    config["secret"] = ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    config["scrapy_project"] = "scrape"
    config["scrapy_admin_email"] = "james@nyle.co"
    config["scrapy_from_email"] = "mail@nyle.co"
    
    setup_virtualenv(script, config)
    install_packages(script, config)
    initialize_project(script, config)
    create_database(script, config)
    set_environment(script, config)
    initialize_south(script, config)
    initialize_scrapy(script, config)
    initialize_celery(script, config)
    script.run()

#!/usr/bin/env python
import tempfile
import subprocess
import os
import re
import random
import urllib


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
        
    def add(self, command, redirect=True, echo=True):
        if echo:
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
    script.add("pip install django-toolbelt")
    script.add("pip install newrelic")
    
        
def initialize_project(script, config):
    script.add_section("Create django project and local git repo")

    script.add("django-admin.py startproject %s" % config['project'])
    script.add("cd %s" % config['project'])
    script.add("git init")
    script.add_template("django/.gitignore", ".")
    script.add_commit("Initial commit of %s" % config['project'])
    script.add_template("django/settings.py", config["project"])
    script.add_template("django/wsgi.py", config["project"], replace=config)
    script.add("pip freeze > requirements.txt", redirect=False)
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
    script.add_commit("Added South for database migrations")
    
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
    script.add_commit("Created a sample Scrapy project and set up integration with Django")
    
def initialize_celery(script, config):
    script.add_section("Initialize Celery") 
    script.add("brew install redis")
    script.add("python manage.py migrate djcelery")
    script.add_template("celery/tasks.py", ".", replace=config)
    script.add_commit("Created a default celery task and set up integration with Django")
    

def initialize_heroku(script, config):
    secret = secret_key()
    
    script.add_section("Initialize Heroku")
    script.add("heroku apps:create %s" % config["heroku_web_app"])
    
    script.add("heroku addons:add %s --app %s" % (config["db_size"], config["heroku_web_app"]))
    script.add("pginfo=`heroku pg:info --app %s`" % config["heroku_web_app"], redirect=False, echo=False)
    script.add("db=`echo $pginfo | sed 's/=== \([A-Z_]*\).*/\\1/'`", redirect=False, echo=False)
    script.add("db_path=`heroku config:get $db --app %s`" % config["heroku_web_app"], redirect=False, echo=False)
    script.add("heroku pg:promote $db --app %s" % config["heroku_web_app"])
    script.add("heroku addons:add redistogo --app %s" % config["heroku_web_app"])
    script.add("heroku addons:add newrelic --app %s" % config["heroku_web_app"])
    
    script.add("heroku apps:create %s" % config["heroku_worker_app"])
    script.add("heroku addons:add redistogo --app %s" % config["heroku_worker_app"])
    script.add("heroku addons:add newrelic --app %s" % config["heroku_worker_app"])
    script.add("heroku config:set DATABASE_URL=$db_path --app %s" % config["heroku_worker_app"])
    
    heroku_set_env(config, config["heroku_web_app"], secret)
    heroku_set_env(config, config["heroku_worker_app"], secret)
    
    script.add_template("heroku/Procfile", ".", replace=config)
    script.add_commit("Installed default Heroku Procfile with web and worker tasks")
    
    script.add_section("Deploy to Heroku Web")
    script.add("git remote add web git@heroku.com:%s.git" % config["heroku_web_app"])
    script.add("ssh-add %s" % config["heroku_ssh"])
    script.add("git push web master")
    script.add("heroku run python manage.py syncdb --app %s" % config["heroku_web_app"], redirect=False)
    script.add("heroku run python manage.py migrate djcelery --app %s" % config["heroku_web_app"])
    script.add("heroku ps:scale web=1 --app %s" % config["heroku_web_app"])
    script.add("heroku ps:scale worker=0 --app %s" % config["heroku_web_app"])
    
    script.add_section("Deploy to Heroku Worker")
    script.add("git remote add worker git@heroku.com:%s.git" % config["heroku_worker_app"])
    script.add("ssh-add %s" % config["heroku_ssh"])
    script.add("git push worker master")
    script.add("heroku ps:scale web=0 --app %s" % config["heroku_worker_app"])
    script.add("heroku ps:scale worker=1 --app %s" % config["heroku_worker_app"])
    
def heroku_set_env(config, app, secret):
    script.add("heroku config:set "
               "TEMPLATE_DEBUG=DEBUG DEBUG=False SECRET_KEY='%s' DJANGO_PROJECT='%s' "
               "EMAIL_HOST='smtp.mandrillapp.com' EMAIL_PORT='587' EMAIL_HOST_USER='%s' "
               "EMAIL_HOST_PASSWORD='%s' EMAIL_USE_TLS=True --app %s" %
               (secret, config["project"], config["mandrill_user"], config["mandrill_password"], app))
    
def heroku_app_exists(app):
    return not re.search(r"Heroku \| No such app", urllib.urlopen("http://%s.herokuapp.com" % app).read())

def prompt_for_heroku_app(config):
    config["heroku_web_app"] = (raw_input("Please pick a name for your heroku app [%s]: "
                                          % config["project"])
                                or config["project"])
    while heroku_app_exists(config["heroku_web_app"]):
        config["heroku_web_app"] = (raw_input("'%s' already exists, please pick a different name [%s]: "
                                              % (config["heroku_web_app"], config["project"])) 
                                    or config["project"])
            
    config["heroku_worker_app"] = "%s-worker" % config["heroku_web_app"]
    i = 1
    while heroku_app_exists(config["heroku_worker_app"]):
        config["heroku_worker_app"] = "%s-worker%s" % (config["heroku_web_app"], i)
        i += 1
        
    upgrade_db = raw_input("Would you like to upgrade your Postgres to 'basic'? (y/n) [n] ")
    config["db_size"] = "heroku-postgresql"
    if upgrade_db == "y":
        config["db_size"] = "heroku-postgresql:basic"
    
def secret_key():
    return ''.join([random.SystemRandom().choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    
if __name__ == '__main__':
    script = ShellScript("setup.log")
    
    print "This script assumes you have a psql server installed and running"
    print "This script assumes you have the heroku toolbelt installed an you're logged in"
    print "Type 'redis-server &' to run the installed redis server"
    
    config = {}
    config["project"] = "blockboard"
    config["db_user"] = "blockboard"
    config["local_db_password"] = "local1"
    config["heroku_db_password"] = "local1"
    config["mandrill_user"] = "james@nyle.co"
    config["mandrill_password"] = "5m1v3p2Y1Kzoivi_FF16dQ"
    config["secret"] = secret_key()
    config["scrapy_project"] = "scrape"
    config["scrapy_admin_email"] = "james@nyle.co"
    config["scrapy_from_email"] = "mail@nyle.co"
    config["heroku_ssh"] = "~/.ssh/heroku_nyle_rsa"
    prompt_for_heroku_app(config)
        
    setup_virtualenv(script, config)
    install_packages(script, config)
    initialize_project(script, config)
    create_database(script, config)
    set_environment(script, config)
    initialize_south(script, config)
    initialize_scrapy(script, config)
    initialize_celery(script, config)
    initialize_heroku(script, config)
    script.run()

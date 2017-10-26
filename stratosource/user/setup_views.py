import tempfile

from django.shortcuts import render, render_to_response
import os
import errno

from stratosource.models import ConfigSetting


def setup_createdb(username = None, password = None):
    from django.db import connections

    ##
    # NOTE: this may not be officially supported (ie. I'm hacking)
    #
    conn = connections['default']
    if username and password:
        conn.settings_dict['USER'] = username
        conn.settings_dict['PASSWORD'] = password
    conn.settings_dict['DATABASE'] = None
    conn.settings_dict['NAME'] = None

    c = conn.cursor()
    # the 'create' command works for MySQL/MariaDB and Postgresql
    c.execute('create database stratosource')
    driver = conn.settings_dict['ENGINE']
    if driver.endswith('mysql'):
        c.execute('use stratosource')

def setup_createdbuser():
    from django.db import connections

    ##
    # NOTE: this may not be officially supported (ie. I'm hacking)
    #
    conn = connections['default']
    c = conn.cursor()
    host = conn.settings_dict['HOST']
    driver = conn.settings_dict['ENGINE']
    if driver.endswith('mysql'):
        if host == 'localhost' or host == '127.0.0.1' or host == '' or host is None:
            c.execute("CREATE USER 'stratosource'@'localhost' IDENTIFIED BY 'stratosource'")
            c.execute("GRANT ALL PRIVILEGES ON *.* TO 'stratosource'@'localhost';")
        else:
            c.execute("CREATE USER 'stratosource'@'%' IDENTIFIED BY 'stratosource'")
            c.execute("GRANT ALL PRIVILEGES ON *.* TO 'stratosource'@'%'")
        c.execute('flush privileges')
    if driver.endswith('postgresql') or driver.endswith('psycopg2'):
        c.execute("CREATE USER stratosource with password 'stratosource'")


def setup_createtables():
    from django.core.management import call_command
    call_command('migrate', '--run-syncdb', database='default', interactive=False)

    # update: this config setup is being done in the migrations module
    # import uuid
    #
    # ConfigSetting(key='uuid', value=uuid.uuid1(), allow_delete=False, masked=False).save()
    # for name in 'rally.login,email.host,email.from'.split(','):
    #     ConfigSetting(key=name, value='', allow_delete=False, masked=False).save()
    # for name in 'rally.enabled,agilezen.enabled'.split(','):
    #     ConfigSetting(key=name, value='', type='check', allow_delete=False, masked=False).save()
    # for name in 'rally.password,agilezen.apikey'.split(','):
    #     ConfigSetting(key=name, value='', allow_delete=False, masked=True).save()


def setup(request, stage):
    from django.db import connections

    if stage == 'start':
        return render(request, 'setup.html', {'stage': '10'})
    if stage == '20':
        # check database connection
        try:
            conn = connections['default']
            conn.cursor()
            return render(request, 'setup.html', {'stage': '30'})
        except Exception as ex:
            return render(request, 'setup.html', {'stage': '20', 'status': 'error', 'desc': str(ex)})

    if stage == '22':
        # create everything
        try:
            setup_createdb(request.POST.get('username'), request.POST.get('password'))
            setup_createdbuser()
            setup_createtables()
            return render(request, 'setup.html', {'stage': '50'})
        except Exception as ex:
            print(ex)
            return render_to_response('setup.html', {'stage': '20', 'status': 'error', 'desc': str(ex)})

    if stage == '25':
        # try creating database
        try:
            setup_createdb()
            setup_createtables()
            return render(request, 'setup.html', {'stage': '50'})
        except Exception as ex:
            print(ex)
            return render_to_response('setup.html', {'error': str(ex)})

    if stage == '30':
        # try to create tables
        try:
            setup_createtables()
            return render_to_response('setup.html', {'stage': '50'})
        except Exception as ex2:
            return render_to_response('setup.html', {'status': 'error', 'desc': str(ex2)})

    if stage == '50':
        # filesystem check
        try:
            if 'CONTAINERIZED' in os.environ:
                try:
                    testfile = tempfile.TemporaryFile(dir='/var/sfrepo')
                    testfile.close()
                except OSError as e:
                    if e.errno == errno.EACCES:
                        return render_to_response('setup.html', {'stage': '57', 'status': 'error', 'desc': 'Unable to write to repo directory'})
            else:
                if os.path.isdir('/var/sfrepo'):
                    try:
                        testfile = tempfile.TemporaryFile(dir='/var/sfrepo')
                        testfile.close()
                    except OSError as e:
                        if e.errno == errno.EACCES:
                            return render_to_response('setup.html', {'stage': '55', 'error': str(e)})
                else:
                    try:
                        os.mkdir('/var/sfrepo')
                    except Exception as ex:
                        return render_to_response('setup.html', {'stage': '55', 'error': str(ex)})

            if 'CONTAINERIZED' in os.environ:
                try:
                    testfile = tempfile.TemporaryFile(dir='/var/sftmp')
                    testfile.close()
                except OSError as e:
                    if e.errno == errno.EACCES:
                        return render_to_response('setup.html', {'stage': '57', 'error': str(e)})
            else:
                if os.path.islink('/var/sftmp'):
                    try:
                        testfile = tempfile.TemporaryFile(dir='/var/sftmp')
                        testfile.close()
                    except OSError as e:
                        if e.errno == errno.EACCES:
                            return render_to_response('setup.html', {'stage': '55', 'error': str(e)})
                else:
                    try:
                        os.link('/tmp', '/var/sftmp')
                    except Exception as ex:
                        return render_to_response('setup.html', {'stage': '55', 'error': str(ex)})

            return render_to_response('setup.html', {'stage': '60'})
        except Exception as ex:
            return render_to_response('setup.html', {'error': str(ex)})

    return render_to_response('setup.html', {'stage': stage})


#####
# Basic install script to setup a dev environment to run Stratosource without using /usr/django (rpm installer)
#
####

if [[ $# -ne 1 ]]; then
    echo 'usage: setup.sh <project directory>'
	exit 0
fi

TARGET=$(readlink -m $1)

REL=`cat /etc/system-release`

echo 'installing dependencies'

if [[ "$REL" =~ ^Fedora.* ]]; then
	yum -y install python python-pip 
	pip install --upgrade pip
	pip install django django-bootstrap3 pyexcelerator pyral
	yum -y install httpd python-suds python-requests python-memcached python-lxml mod_wsgi MySQL-python wget git cgit unzip mysql mariadb-server tzlocal
else
	yum -y install epel-release
	yum clean all
	yum -y install python python-pip
	pip install --upgrade pip
	pip install django django-bootstrap3 pyexcelerator pyral
	yum -y install httpd python-suds python-requests python-memcached python-lxml mod_wsgi MySQL-python wget git cgit unzip mysql mariadb-server tzlocal

fi

echo 'configuring apache'

eval grep django /etc/httpd/conf/httpd.conf
# if apache not already configured for django, do it now
if [ $? -eq 1 ]; then
  SITEPKG=`python -c "from distutils.sysconfig import get_python_lib; print get_python_lib()"`
  cat  < $TARGET/resources/httpd-append.conf >> /etc/httpd/conf/httpd.conf 
  sed -i "s|PYTHON_SITEPKG|$SITEPKG|" /etc/httpd/conf/httpd.conf
fi

echo 'configure mysql'
# fix a bug in the mysql rpm installer that does not set correct permissions
mysql_install_db
chown -R mysql.mysql /var/lib/mysql
touch /var/log/mysqld.log
chown mysql:mysql /var/log/mysqld.log
mkdir /var/run/mysqld
chown mysql:mysql /var/run/mysqld

echo 'configuring cgit'
eval grep django /etc/cgitrc
if [ $? -eq 1 ]; then
  echo "include=$TARGET/resources/cgitrepo" >>/etc/cgitrc
fi
if [ ! -f /usr/django/cgitrepo ]; then
  cp /usr/django/resources/cgitrepo /usr/django/stratosource
  chmod 777 /usr/django/stratosource/cgitrepo
fi

cp /usr/django/resources/memcached /etc/sysconfig
mkdir $TARGET/logs
chmod 777 $TARGET/logs
mkdir /var/sfrepo
chmod 777 /var/sfrepo
ln -s /var/sftmp /tmp
chmod 777 /var/sftmp

echo 'restarting services'
service memcached restart
service httpd restart
service mysqld restart


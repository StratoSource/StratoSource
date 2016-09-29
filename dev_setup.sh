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

FIRST_INSTALL='no'

if [[ "$REL" =~ ^Fedora.* ]]; then
	yum -y install python python-pip httpd mod_wsgi MySQL-python wget git cgit unzip mysql mariadb-server tzlocal
	pip install --upgrade pip
	pip install -r resources/requirements.txt
else
	yum -y install epel-release
	yum clean all
	yum -y install python python-pip httpd mod_wsgi MySQL-python wget git cgit unzip mysql mariadb-server tzlocal
	pip install --upgrade pip
	pip install -r resources/requirements.txt

fi

if [ ! -f /etc/httpd/conf.d/stratosource.conf ]; then
  echo 'configuring apache'
  cp resources/httpd.conf /etc/httpd/conf.d/stratosource.conf
  FIRST_INSTALL='yes'
fi


if [ $FIRST_INSTALL == 'yes' ]; then
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
    echo "include=/var/sfrepo/config/cgitrepo" >>/etc/cgitrc
  fi
  if [ ! -f /var/sfrepo/config/cgitrepo ]; then
    cp /usr/django/resources/cgitrepo /var/sfrepo/config
    chmod 777 /var/sfrepo/config/cgitrepo
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


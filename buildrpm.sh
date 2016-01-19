##
# Update version numbers here only
##
MAJOR=2
MINOR=12
PATCH=0
REL=0
VERSION=$MAJOR.$MINOR.$PATCH
NAME=stratosource-$VERSION

rm -rf latest/*.rpm
rm -rf $NAME
mkdir $NAME
cp -R stratosource $NAME
cp -R resources $NAME
cp *cronjob.sh $NAME
cp notify.py $NAME
cp runmanage.sh $NAME

SOURCEDIR="/tmp/stratosource"
mkdir -p $SOURCEDIR/SOURCES
tar czf $SOURCEDIR/SOURCES/$NAME-$REL.tar.gz $NAME/*
cp specs/stratosource.spec.template specs/stratosource.spec
sed -i "s/Version:/Version: $VERSION/" specs/stratosource.spec
sed -i "s/Release:/Release: $REL/" specs/stratosource.spec
rpmbuild -v -bb --target=noarch --define="_topdir $SOURCEDIR" specs/stratosource.spec
rm -rf $NAME
cp $SOURCEDIR/RPMS/noarch/* latest/
echo "Cleaning Up Build Directory"
rm -rf $SOURCEDIR/

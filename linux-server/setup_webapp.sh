path='/root/udacity-nano-fullstack/linux-server/'
USER=catalog
targetpath='/var/www/catalog'

mkdir /var/www/catalog
cp -R $path"catalog" $targetpath
cp $path"catalog.wsgi" $targetpath/catalog.wsgi

# rename application.py
mv $targetpath"/catalog/application.py" $targetpath"/catalog/catalog.py"
# remove old sqlite db
rm $targetpath"/catalog.db"

chown -R $USER:$USER $targetpath
chmod -R 755 /var/www

# this got rid of the permission denied error when uploading
# but is weird!
chmod -R 777 /var/www/catalog/catalog/uploads

# copy conf
cp $path"catalog.conf" /etc/apache2/sites-available/catalog.conf

# create symbolic link and enable site
a2ensite catalog.conf

# reload server to apply the change
service apache2 reload

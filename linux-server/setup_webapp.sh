path='/root/udacity-nano-fullstack/linux-server/'
USER=catalog
target_path = '/var/www/catalog'

mkdir /var/www/catalog
cp -R $path"catalog" $target_path
cp $path"catalog.wsgi" $target_path/catalog.wsgi
chown -R $USER:$USER $target_path
chmod -R 755 /var/www

# copy conf
cp $path"catalog.conf" /etc/apache2/sites-available/catalog.conf

# create symbolic link and enable site
a2ensite catalog.conf

# reload server to apply the change
service apache2 reload

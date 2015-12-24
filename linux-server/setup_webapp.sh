path='/root/udacity-nano-fullstack/linux-server/catalog/'
USER=catalog

mkdir /var/www/catalog
cp -R $path /var/www/catalog
chown -R $USER:$USER /var/www/catalog
chmod -R 755 /var/www

# copy conf
cp $path"catalog.conf" /etc/apache2/sites-available/catalog.conf

# create symbolic link and enable site
a2ensite catalog.conf

# reload server to apply the change
service apache2 reload

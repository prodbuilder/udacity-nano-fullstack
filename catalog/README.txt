Item Catalog
=========

# Startup Guide
To setup initial data
```python
python add_data.py
```

To start the app, run from Vagrant
```python
python application.py
```
And open the web app from `http://localhost:5432`

# Basic Funtionalities

Home page of the catalog app displays up to 30 recently added items.

## JSON APIs

Get results in JSON format:
- `/categories.json`: All categories
- `/category/<int:category_id>/items.json`: All items in a category
- `/category/<int:category_id>/item/<int:item_id>.json`: An item in a category
- `/items.json`: All items in catalog
- `/item/<int:item_id>.json`: An item by id
- `/catalog.json`: the whole catalog by category

## XML API

As demo only, `http://localhost:5432/catalog.xml` displays the same catalog data in XML.

## CRUD and OAuth with Google+ and Facebook
- You may login using your google+ or facebook account. 
- You will be able to view any items, but only add new items after you login. 
- You are only allowed to edited and delete items created by yourself.
- You can upload a picture for each item. Some items have pre-populated pictures.

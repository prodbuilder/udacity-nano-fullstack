#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#--------------------------------------------------------------
#
# Item Catalog App
#
#--------------------------------------------------------------
#
# Date:   2015-12-10
#
# Author: Yu Guo <yuguo01462@gmail.com>
#


from flask import Flask, render_template, request, redirect,jsonify, url_for, flash, send_from_directory
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import json
import requests
import os

import xml.etree.ElementTree as ET
from xml.dom import minidom
from dict2xml import dict2xml as xmlify
from flask.ext.seasurf import SeaSurf
from helper import *


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
csrf = SeaSurf(app)

curr_path =  os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
#--------------------------------------------------------------
# Global Functions
#--------------------------------------------------------------

#--------------------------------------------------------------
# 0. Show Error status slightly nicely
#--------------------------------------------------------------

# Sample HTTP error handling
@app.errorhandler(404)
def notFound(error):
    return render_template('404.html'), 404

# Sample HTTP error handling
@app.errorhandler(500)
def internalError(error):
    return render_template('500.html'), 500

#--------------------------------------------------------------
# 1. User Login/Logout Functions
#--------------------------------------------------------------

@app.route('/login', methods = ['GET', 'POST'])
def login():
    # Create anti-forgery state token
    login_session['state'] = getStateToken()
    return render_template('login.html', categories = getCategories(), STATE = login_session['state'])


@app.route('/logout', methods = ['GET', 'POST'])
def logout():
    if 'username' in login_session:
        if login_session.get('provider'):
            if login_session['provider'] == 'google':
                gdisconnect()
                del login_session['gplus_id']
                del login_session['credentials']
            if login_session['provider'] == 'facebook':
                fbdisconnect()
                del login_session['facebook_id']
                del login_session['access_token']
            del login_session['provider']

        del login_session['username']
        del login_session['email']
        del login_session['user_id']
        del login_session['picture']
        flash("You have successfully been logged out.")
    else:
        flash("You were not logged in")
    return redirect(url_for('index'))


# Facebook connect
@csrf.exempt
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    invalid_state_token = request.args.get('state') != login_session['state']
    if invalid_state_token:
        return returnResponseJSON('Invalid state parameter.', 401)

    access_token = request.data
    client_secret = json.loads(open(
        os.path.join(curr_path, 'fb_client_secrets.json'), 'r').read())['web']
    app_id = client_secret['app_id']
    app_secret = client_secret['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)
    result = requests.get(url).text
    # strip expire tag from access token
    token = result.split("&")[0]
    login_session['provider'] = 'facebook'
    login_session['access_token'] = token.split("=")[1]

    # Use token to get user info from API
    url = 'https://graph.facebook.com/v2.4/me?%s&fields=name,id,email' % token
    data = json.loads(requests.get(url).text)

    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # Get user picture
    url = 'https://graph.facebook.com/v2.4/me/picture?%s&redirect=0&height=200&width=200' % token
    data = json.loads(requests.get(url).text)
    login_session['picture'] = data["data"]["url"]

    # see if user exists, if it doesn't make a new one
    login_session['user_id'] = loginOrCreateNew(getUserID(login_session["email"]), login_session)

    output = """<h1>Welcome, %s!</h1> <img src="%s" style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">""" % (login_session['username'], login_session['picture'])
    flash("you are now logged in as %s" % login_session['username'])
    return output

@csrf.exempt
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    result = requests.delete(url)
    if result.status_code != '200':
        return returnResponseJSON('Failed to revoke token for given user.', 400)

# Google connect
@csrf.exempt
@app.route('/gconnect', methods=['POST'])
def gconnect():
    invalid_state_token = request.args.get('state') != login_session['state']
    if invalid_state_token:
        return returnResponseJSON('Invalid state parameter.', 401)

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(os.path.join(curr_path, 'google_client_secrets.json'), scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(request.data)
    except FlowExchangeError:
        return returnResponseJSON('Failed to upgrade the authorization code.', 401)

    # Check that the access token is valid.
    access_token = credentials.access_token
    result = json.loads(requests.get('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token).text)
    invalid_access_token = result.get('error') is not None
    if invalid_access_token:
        return returnResponseJSON(result.get('error'), 500)

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        return returnResponseJSON("Token's user ID doesn't match given user ID.", 401)

    # Verify that the access token is valid for this app.
    if result['issued_to'] != oauth_flow.client_id:
        return returnResponseJSON("Token's client ID does not match app's.", 401)

    # Check if user is already logged in
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        return returnResponseJSON('Current user is already connected.', 200)

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    login_session['provider'] = 'google'

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params).json()

    login_session['username'] = answer['name']
    login_session['picture'] = answer['picture']
    login_session['email'] = answer['email']

    # see if user exists, if it doesn't make a new one
    login_session['user_id'] = loginOrCreateNew(getUserID(answer["email"]), login_session)

    output = """<h1>Welcome, %s!</h1> <img src="%s" style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">""" % (login_session['username'], login_session['picture'])
    flash("you are now logged in as %s" % login_session['username'])
    return output


@csrf.exempt
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        return returnResponseJSON('Current user not connected.', 401)

    result = requests.get('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % credentials)
    if result.status_code != '200':
        return returnResponseJSON('Failed to revoke token for given user.', 400)

#--------------------------------------------------------------
# 2a. JSON APIs to view category and item information
#--------------------------------------------------------------

# JSON API to view category information
@app.route('/categories.json')
def categoriesJSON():
    categories = getCategories()
    return jsonify(categories = [c.serialize for c in categories])

# JSON API to view all items in a category
@app.route('/category/<int:category_id>/items.json')
def categoryItemsJSON(category_id):
    category_items = getCategoryItemsByCategoryId(category_id)
    return jsonify(items = [i.serialize for i in category_items])

# JSON API to view an item in a category by id
@app.route('/category/<int:category_id>/item/<int:item_id>.json')
def categoryItemJSON(category_id, item_id):
    item = getItemByCategoryIdItemId(category_id, item_id)
    return jsonify(item = item.serialize)

# JSON API to view all items
@app.route('/items.json')
def itemsJSON():
    items = getAllItems()
    return jsonify(items = [i.serialize for i in items])

# JSON API to view an item by id
@app.route('/item/<int:item_id>.json')
def itemJSON(item_id):
    item = getItemById(item_id)
    return jsonify(item = item.serialize)


# JSON API to view all items by category
@app.route('/catalog.json')
def catalogJSON():
    res = baseCatalog()
    return jsonify(Categories = res)

#--------------------------------------------------------------
# 2b. XML API demo
#--------------------------------------------------------------

# XML API to view all items by category
@app.route('/catalog.xml')
def catalogXML():
    res = {'category': baseCatalog()}
    catalog = xmlify(res, wrap = "Categories", indent="  ")
    return returnResponseXML(catalog, 200)



#--------------------------------------------------------------
# 3. Show category and items
#--------------------------------------------------------------

# Helper function to show uploaded files
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Show all categories
@app.route('/')
def index():
    return render_template('ShowItems.html', \
                            categories = getCategories(), \
                            items = getLatestItems(), \
                            title='Latest Items')

# Show all items in a category by name
@app.route('/catalog/<path:category_name>/items/')
def showCategoryItemsByName(category_name):
    category_items = getCategoryItems(category_name)
    return render_template('ShowItems.html', \
                            categories = getCategories(), \
                            items = category_items, \
                            category_name = category_name, \
                            title = '%s Items (%s items)' % (category_name, len(category_items)))

# Show a particular item in a category by name
@app.route('/catalog/<path:category_name>/<path:item_name>/')
def showCategoryItemByName(category_name, item_name):
    return render_template('ShowItem.html', \
                            categories = getCategories(), \
                            item = getItemByName(category_name, item_name), \
                            category_name = category_name)

#--------------------------------------------------------------
# 4. Create, Update, Delete items
#--------------------------------------------------------------

#--------------------------------------------------------------
# Decorator for login required
#--------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


# Create new item
@app.route('/item/new', methods = ['GET', 'POST'])
@login_required
def createAnyItem():
    if request.method == 'POST':
        if request.form['name'] and request.form['description']:
            newItem = addNewItem(request.form['name'],
                                 request.form['description'],
                                 request.files['file'],
                                 login_session['user_id'],
                                 request.form['category_name'])
            flash('New Item %s has been successfully created!' % newItem.name)
            return redirect(url_for('index'))
    else:
        return render_template('NewItem.html', categories = getCategories())


# Create new category item by category name
@app.route('/catalog/<path:category_name>/item/new', methods = ['GET', 'POST'])
@login_required
def createCategoryItemByName(category_name):
    if request.method == 'POST':
        category_id = getCategoryName(category_name)
        if request.form['name'] and request.form['description'] and category_id:
            newItem = addNewItem(request.form['name'],
                                 request.form['description'],
                                 request.files['file'],
                                 login_session['user_id'],
                                 category_name)
            flash('New Item %s has been successfully created in %s!' % (newItem.name, category_name))
            return redirect(url_for('showCategoryItemsByName', category_name = category_name))
        return render_template('NewItem.html', categories = getCategories(), category_name = category_name)
    else:
        return render_template('NewItem.html', categories = getCategories(), category_name = category_name)


# Edit an item by category and item name
@app.route('/catalog/<path:category_name>/<path:item_name>/edit', methods = ['GET', 'POST'])
@login_required
def editItemByName(category_name, item_name):
    editedItem = getItemByName(category_name, item_name)

    if editedItem.user_id != login_session['user_id']:
        flash("You can not edit someone else's item!")
        return redirect(url_for('showCategoryItemsByName', category_name = category_name))

    if request.method == 'POST':
        editedItem = editItem(editedItem, request.form['name'], request.form['description'], request.files['file'])
        flash('Item %s has been successfully edited!' % editedItem.name)
        return redirect(url_for('showCategoryItemByName', category_name=category_name, item_name=editedItem.name))
    else:
        return render_template('EditItem.html', categories = getCategories(), item = editedItem, category_name = editedItem.category.name)


# Delete an item by category and item name
@app.route('/catalog/<path:category_name>/<path:item_name>/delete', methods = ['GET', 'POST'])
@login_required
def deleteItemByName(category_name, item_name):
    deletedItem = getItemByName(category_name, item_name)

    if deletedItem.user_id != login_session['user_id']:
        flash("You can not delete someone else's item!")
        return redirect(url_for('showCategoryItemsByName', category_name=category_name))

    if request.method == 'POST':
        deleteItem(deletedItem)
        flash('Item %s has been successfully deleted!' %item_name)
        return redirect(url_for('showCategoryItemsByName', category_name=category_name))
    else:
        return render_template('DeleteItem.html', categories = getCategories(), item = deletedItem)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = False
    app.run(host = '127.0.0.1', port = 5050)
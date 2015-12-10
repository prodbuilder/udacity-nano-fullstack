from flask import Flask, render_template, request, redirect,jsonify, url_for, flash, send_from_directory
from sqlalchemy import create_engine, asc, desc, func
from sqlalchemy.orm import sessionmaker
from db import Base, User, Category, Item
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import json
from flask import make_response
import requests
import os
from werkzeug import secure_filename
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

#--------------------------------------------------------------
# Global Constants & Vars
#--------------------------------------------------------------


# Enable protection agains *Cross-site Request Forgery (CSRF)*
CSRF_ENABLED     = True

#Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession(autocommit=True)

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

# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session['email'], picture=login_session['picture'])
    session.add(newUser)
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id

def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user

def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

def loginOrCreateNew(user_id):
    if not user_id:
        user_id = createUser(login_session)
    return user_id

def getStateToken():
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))

@app.route('/login', methods = ['GET', 'POST'])
def login():
    # Create anti-forgery state token
    state = getStateToken()
    login_session['state'] = state
    categories = session.query(Category).order_by(asc(Category.name))
    return render_template('login.html', categories = categories, STATE = state)


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

def returnResponseJSON(msg, code):
    """helper function to make a json response msg"""
    response = make_response(json.dumps(msg), code)
    response.headers['Content-Type'] = 'application/json'
    return response


# Facebook connect

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    invalid_state_token = request.args.get('state') != login_session['state']
    if invalid_state_token:
        return returnResponseJSON('Invalid state parameter.', 401)

    access_token = request.data
    client_secret = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']
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
    login_session['user_id'] = loginOrCreateNew(getUserID(login_session["email"]))

    output = """<h1>Welcome, %s!</h1> <img src="%s" style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">""" % (login_session['username'], login_session['picture'])
    flash("you are now logged in as %s" % login_session['username'])
    return output

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
@app.route('/gconnect', methods=['POST'])
def gconnect():
    invalid_state_token = request.args.get('state') != login_session['state']
    if invalid_state_token:
        return returnResponseJSON('Invalid state parameter.', 401)

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('google_client_secrets.json', scope='')
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
    login_session['user_id'] = loginOrCreateNew(getUserID(answer["email"]))

    output = """<h1>Welcome, %s!</h1> <img src="%s" style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">""" % (login_session['username'], login_session['picture'])
    flash("you are now logged in as %s" % login_session['username'])
    return output


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
    categories = session.query(Category).order_by(asc(Category.name)).all()
    return jsonify(categories = [c.serialize for c in categories])

# JSON API to view all items in a category
@app.route('/category/<int:category_id>/items.json')
def categoryItemsJSON(category_id):
    category_items = session.query(Item).filter_by(category_id = category_id).all()
    return jsonify(items = [i.serialize for i in category_items])

# JSON API to view an item in a category by id
@app.route('/category/<int:category_id>/item/<int:item_id>.json')
def categoryItemJSON(category_id, item_id):
    item = session.query(Item).filter_by(category_id = category_id, id = item_id).one()
    return jsonify(item = item.serialize)

# JSON API to view all items
@app.route('/items.json')
def itemsJSON():
    items = session.query(Item).order_by(asc(Item.name)).all()
    return jsonify(items = [i.serialize for i in items])

# JSON API to view an item by id
@app.route('/item/<int:item_id>.json')
def itemJSON(item_id):
    item = session.query(Item).filter_by(id = item_id).one()
    return jsonify(item = item.serialize)

# JSON API to view all items by category
@app.route('/catalog.json')
def catalogJSON():
    categories = session.query(Category).order_by(asc(Category.name)).all()
    res = []
    for c in categories:
        category_items = session.query(Item).filter_by(category_id = c.id).all()
        a = c.serialize
        a.update({'items': [i.serialize for i in category_items]})
        res.append(a)
    return jsonify(Categories = res)

#--------------------------------------------------------------
# 2b. XML API demo
#--------------------------------------------------------------

# XML API to view all items by category
@app.route('/catalog.xml')
def catalogXML():
    categories = session.query(Category).order_by(asc(Category.name)).all()
    res = []
    for c in categories:
        category_items = session.query(Item).filter_by(category_id = c.id).all()
        a = c.serialize
        items = []
        for i in category_items:
            tmp = i.serialize
            tmp.update({'author': i.user.name})
            items.append(tmp)
        a.update({'items': items})
        res.append(a)
    catalog = render_template('catalog_template.xml', categories = res)
    response = make_response(catalog, 200)
    response.headers['Content-Type'] = 'application/xml'
    return response


#--------------------------------------------------------------
# 3. Show category and items
#--------------------------------------------------------------

# Helper function to show uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# helper function: get category id from category name
def getCategoryName(category_name):
    return session.query(Category).filter(func.lower(Category.name) == func.lower(category_name)).one().id

# Show all categories
@app.route('/')
def index():
    categories = session.query(Category).order_by(asc(Category.name))
    items = session.query(Item).order_by(desc(Item.last_updated)).limit(30)
    return render_template('ShowItems.html', categories = categories, items = items, title='Latest Items')

# Show all items in a category by name
@app.route('/catalog/<category_name>/items/')
def showCategoryItemsByName(category_name):
    categories = session.query(Category).order_by(asc(Category.name))
    category_id = getCategoryName(category_name)
    category_items = session.query(Item).join(Item.category).filter(Category.name == category_name).all()
    return render_template('ShowItems.html', categories = categories, items = category_items,
        category_name = category_name,
        title = '%s Items (%s items)' % (category_name, len(category_items)))

# Show a particular item in a category by name
@app.route('/catalog/<category_name>/<item_name>/')
def showCategoryItemByName(category_name, item_name):
    categories = session.query(Category).order_by(asc(Category.name))
    category_id = getCategoryName(category_name)
    item = session.query(Item).join(Item.category).filter(Category.name == category_name, Item.name == item_name).one()
    # item = session.query(Item).filter_by(category_id = category_id, id = item_id).one()
    return render_template('ShowItem.html', categories = categories, item = item, category_name = category_name)

#--------------------------------------------------------------
# 4. Create, Update, Delete items
#--------------------------------------------------------------

# Helper function to allow certain extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

# Helper add picture
def add_pic(file):
    """Helper function to save uploaded file and return filename"""
    if file and allowed_file(file.filename):
        # add timestamp to differentiate between files with same name
        filename = str(int(time.time())) + secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename

# Create new item
@app.route('/item/new', methods = ['GET', 'POST'])
def createAnyItem():
    categories = session.query(Category).order_by(asc(Category.name))
    if 'username' not in login_session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        # CSRF check
        if request.form.get('csrfmiddlewaretoken') != login_session['csrf_token']:
            return returnResponseJSON('Invalid state parameter.', 401)
        category_id = getCategoryName(request.form['category_name'])
        picture = add_pic(request.files['file'])
        newItem = Item(name = request.form['name'], description = request.form['description'], category_id = category_id, user_id = login_session['user_id'], picture = picture)
        session.add(newItem)
        flash('New Item %s has been successfully created!' % newItem.name)
        return redirect(url_for('index'))
    else:
        token = getStateToken()
        login_session['csrf_token'] = token
        return render_template('NewItem.html', categories = categories, csrf_token = token)


# Create new category item by category name
@app.route('/catalog/<category_name>/item/new', methods = ['GET', 'POST'])
def createCategoryItemByName(category_name):
    categories = session.query(Category).order_by(asc(Category.name))
    category_id = getCategoryName(category_name)
    if 'username' not in login_session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        # CSRF check
        if request.form.get('csrfmiddlewaretoken') != login_session['csrf_token']:
            return returnResponseJSON('Invalid state parameter.', 401)

        if request.form['name'] and request.form['description'] and category_id and login_session['user_id']:
            picture = add_pic(request.files['file'])
            newItem = Item(name = request.form['name'], description = request.form['description'], category_id = category_id, user_id = login_session['user_id'], picture = picture)
            session.add(newItem)
            flash('New Item %s has been successfully created!' % newItem.name)
            return redirect(url_for('showCategoryItemsByName', category_name = category_name))

        token = getStateToken()
        login_session['csrf_token'] = token
        return render_template('NewItem.html', categories = categories, category_name = category_name, csrf_token = token)
    else:
        token = getStateToken()
        login_session['csrf_token'] = token
        return render_template('NewItem.html', categories = categories, category_name = category_name, csrf_token = token)


# Edit an item by category and item name
@app.route('/catalog/<category_name>/<item_name>/edit', methods = ['GET', 'POST'])
def editItemByName(category_name, item_name):
    categories = session.query(Category).order_by(asc(Category.name))
    category_id = getCategoryName(category_name)
    editedItem = session.query(Item).filter_by(category_id = category_id, name = item_name).one()
    if 'username' not in login_session:
        flash('You need to login in order to edit an item.')
        return redirect(url_for('login'))
    if editedItem.user_id != login_session['user_id']:
        flash("You can not edit someone else's item!")
        return redirect(url_for('showCategoryItemsByName', category_name = category_name))

    if request.method == 'POST':
        # CSRF check
        if request.form.get('csrfmiddlewaretoken') != login_session['csrf_token']:
            return returnResponseJSON('Invalid state parameter.', 401)

        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        picture = add_pic(request.files['file'])
        if picture:
            editedItem.picture = picture
        session.add(editedItem)
        flash('Item %s has been successfully edited!' % editedItem.name)
        return redirect(url_for('showCategoryItemByName', category_name=category_name, item_name=editedItem.name))
    else:
        token = getStateToken()
        login_session['csrf_token'] = token
        return render_template('EditItem.html', categories = categories, item = editedItem, category_name = editedItem.category.name, csrf_token = token)


# Delete an item by category and item name
@app.route('/catalog/<category_name>/<item_name>/delete', methods = ['GET', 'POST'])
def deleteItemByName(category_name, item_name):
    categories = session.query(Category).order_by(asc(Category.name))
    category_id = getCategoryName(category_name)
    deleteItem = session.query(Item).filter_by(category_id = category_id, name = item_name).one()
    if 'username' not in login_session:
        flash('You need to login in order to delete an item.')
        return redirect(url_for('login'))
    if deleteItem.user_id != login_session['user_id']:
        flash("You can not delete someone else's item!")
        return redirect(url_for('showCategoryItemsByName', category_name=category_name))
    if request.method == 'POST':
        # CSRF check
        if request.form.get('csrfmiddlewaretoken') != login_session['csrf_token']:
            return returnResponseJSON('Invalid state parameter.', 401)

        session.delete(deleteItem)
        flash('Item has been successfully deleted!')
        return redirect(url_for('showCategoryItemsByName', category_name=category_name))
    else:
        token = getStateToken()
        login_session['csrf_token'] = token
        return render_template('DeleteItem.html', categories = categories, item = deleteItem, csrf_token = token)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5432)
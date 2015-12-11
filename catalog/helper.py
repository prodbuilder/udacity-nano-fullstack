#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#--------------------------------------------------------------
#
# Helper functions for Item Catalog App
#
#--------------------------------------------------------------
#
# Date:   2015-12-10
#
# Author: Yu Guo <yuguo01462@gmail.com>
#

from sqlalchemy import create_engine, asc, desc, func
from sqlalchemy.orm import sessionmaker
from db import Base, User, Category, Item
import random
import string
from functools import wraps
from flask import make_response
import os
import time
from werkzeug import secure_filename
import json

#--------------------------------------------------------------
# Global Constants & Vars
#--------------------------------------------------------------

#Connect to Database and create database session
engine = create_engine('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession(autocommit=True)


UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


#--------------------------------------------------------------
# User Helper Functions
#--------------------------------------------------------------
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

def loginOrCreateNew(user_id, login_session):
    if not user_id:
        user_id = createUser(login_session)
    return user_id

def getStateToken():
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))

#--------------------------------------------------------------
# Helper for generating json/xml response
#--------------------------------------------------------------
def returnResponseJSON(msg, code):
    """helper function to make a json response msg"""
    response = make_response(json.dumps(msg), code)
    response.headers['Content-Type'] = 'application/json'
    return response

def returnResponseXML(data, code):
    """helper function to make a xml response msg"""
    head = '<?xml version="1.0" encoding="UTF-8"?>\n'
    response = make_response(head + data, code)
    response.headers['Content-Type'] = 'application/xml'
    return response


#--------------------------------------------------------------
# Helper for uploading picture
#--------------------------------------------------------------

# Allow certain extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def add_pic(file):
    """Helper function to save uploaded file and return filename"""
    if file and allowed_file(file.filename):
        # add timestamp to differentiate between files with same name
        filename = str(int(time.time())) + secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return filename

def delete_pic(filename):
    if filename:
        abs_filename = os.path.join(UPLOAD_FOLDER, filename)
        os.remove(abs_filename)

#--------------------------------------------------------------
# Data Access Objects
#--------------------------------------------------------------

def getCategories():
    return session.query(Category).order_by(asc(Category.name)).all()

def getCategoryItemsByCategoryId(category_id):
    return session.query(Item).filter_by(category_id = category_id).all()

def getCategoryItems(category_name):
    return session.query(Item).join(Item.category).filter(Category.name == category_name).all()

def getItemByCategoryIdItemId(category_id, item_id):
    return session.query(Item).filter_by(category_id = category_id, id = item_id).one()

def getItemByName(category_name, item_name):
    return session.query(Item).join(Item.category).filter(Category.name == category_name, Item.name == item_name).one()

def getAllItems():
    return session.query(Item).order_by(asc(Item.name)).all()

def getLatestItems(max=30):
    return session.query(Item).order_by(desc(Item.last_updated)).limit(max)

def getItemById(item_id):
    return session.query(Item).filter_by(id = item_id).one()


# Get category id from category name
def getCategoryName(category_name):
    return session.query(Category).filter(func.lower(Category.name) == func.lower(category_name)).one().id


# Get base catalog data
def baseCatalog():
    categories = session.query(Category).order_by(asc(Category.name)).all()
    res = []
    for c in categories:
        category_items = session.query(Item).filter_by(category_id = c.id).all()
        a = c.serialize
        a.update({'items': [i.serialize for i in category_items]})
        res.append(a)
    return res


def addNewItem(name, description, file, author, category_name):
    category_id = getCategoryName(category_name)
    picture = add_pic(file)
    newItem = Item(name = name, description = description, category_id = category_id, user_id = author, picture = picture)
    session.add(newItem)
    return newItem

def editItem(editedItem, name, description, file):
    if name:
        editedItem.name = name
    if description:
        editedItem.description = description
    picture = add_pic(file)
    if picture:
        editedItem.picture = picture
    session.add(editedItem)
    return editedItem

def deleteItem(deletedItem):
    delete_pic(deletedItem.picture)
    session.delete(deletedItem)



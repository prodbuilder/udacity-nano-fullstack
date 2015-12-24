from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from collections import namedtuple
from db import Base, User, Category, Item
import random

class DataCreater(object):

    def __init__(self, DB_NAME):
        self.get_session(DB_NAME)
        self.define_users()
        self.define_categories()
        self.define_items()

    def get_session(self, DB_NAME):
        engine = create_engine('postgresql://catalog:udacity@localhost/catalog')

        Base.metadata.bind = engine
        DBSession = sessionmaker(bind=engine)
        self.session = DBSession(autocommit = True)

    def define_users(self):
        user1 = User(name='User1', email='yuguo01462@gmail.com')
        user2 = User(name='User2', email='email2')
        self.users = [user1, user2]

    def define_categories(self):
        cats = ['Soccer', 'Basketball', 'Baseball', 'Frisbee', 'Snowboarding', 'Rock Climbing', 'Foosball', 'Skating', 'Hockey']
        self.categories = dict((cat, Category(name = cat, user = random.choice(self.users))) for cat in cats)

    def define_items(self):
        CatItem = namedtuple('Category_Items', 'name,description,category,user,picture')
        self.items = [
            CatItem('Soccer Cleats', 'Some generic description for Soccer Cleats', self.categories['Soccer'], random.choice(self.users), ''),
            CatItem('Jersey', 'Some generic description for Jsersey', self.categories['Soccer'], random.choice(self.users), ''),
            CatItem('Bat', 'Some generic description for Baseball Bat', self.categories['Baseball'], random.choice(self.users), 'baseball_bat.jpeg'),
            CatItem('Frisbee', 'Some generic description for Frisbee', self.categories['Frisbee'], random.choice(self.users), 'freesbie.jpeg'),
            CatItem('Shinguards', 'Some generic description for Shinguards', self.categories['Soccer'], random.choice(self.users), ''),
            CatItem('Twin shiguards', 'Some generic description for Twin shiguards', self.categories['Soccer'], random.choice(self.users), ''),
            CatItem('Snowboard', 'Some generic description for Snowboard', self.categories['Snowboarding'], random.choice(self.users), 'snowboard.jpeg'),
            CatItem('Goggles', 'Some generic description for Goggles', self.categories['Snowboarding'], random.choice(self.users), ''),
            CatItem('Stick', 'Some generic description for Hockey Stick', self.categories['Hockey'], random.choice(self.users), '')]

    def add_users(self):
        for user in self.users:
            self.session.add(user)

    def add_categories(self):
        for cat, v in self.categories.iteritems():
            self.session.add(v)

    def add_items(self):
        for i in self.items:
            self.session.add(Item(name=i.name, description = i.description, category = i.category, user=i.user, picture = i.picture))

    def list_users(self):
        print 'list users:'
        for each in self.session.query(User).all():
            print '  %s: %s' %(each.name, each.email)

    def list_categories(self):
        print 'list categories:'
        for each in self.session.query(Category).all():
            print '  %s - by %s' %(each.name, each.user.name)

    def list_items(self):
        print 'list items:'
        for each in self.session.query(Item).all():
            print '  %s (%s) [%s] %s - by %s' %(each.name, each.category.name, each.last_updated, each.picture, each.user.name)
            print '    %s' %each.description

    def create(self):
        self.add_users()
        self.add_categories()
        self.add_items()

    def show(self):
        self.list_users()
        self.list_categories()
        self.list_items()

        user2 = self.session.query(User).filter_by(email=u'email2').one()
        print user2.name, user2.id, user2.email, user2.picture

def main():
    creater = DataCreater(DB_NAME)
    creater.create()
    creater.show()


if __name__ == '__main__':
    main()
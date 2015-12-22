#!/usr/bin/env python

"""
conference.py -- Udacity conference server-side Python App Engine API;
    uses Google Cloud Endpoints
"""

__author__ = 'yuguo01462@gmail.com (Yu Guo)'


from datetime import datetime

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import ConflictException
from models import Profile
from models import ProfileMiniForm
from models import ProfileForm

from models import StringMessage
from models import StringMessages
from models import BooleanMessage

from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms
from models import TeeShirtSize

from models import Session
from models import SessionForm
from models import SessionForms
from models import SessionType

from settings import WEB_CLIENT_ID
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE

from utils import getUserId
from utils import debug

from collections import defaultdict

# - - - - - - GLOBAL Variables - - - - - - - - - - - - - - -


EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

# - - - - - - - memcache - - - - - - - - - - - - - - - - - -
MEMCACHE_ANNOUNCEMENTS_KEY = "RECENT_ANNOUNCEMENTS"
ANNOUNCEMENT_TPL = ('Last chance to attend! The following conferences '
                    'are nearly sold out: %s')

MEMCACHE_FEATUREDSPEAKER_KEY = "FEATURED SPEAKERS"
FEATURED_SPEAKER_TPL = ('Featured Speaker %s will speak at %s sessions at %s:\nThey are %s.')



# Default form values
DEFAULTS = {
    "city": "Default City",
    "maxAttendees": 0,
    "seatsAvailable": 0,
    "topics": [ "Default", "Topic" ],
}
SESSION_DEFAULTS = {
    "highlights": False,
    "duration": 0,
}

# Query field and operators
OPERATORS = {
            'EQ':   '=',
            'GT':   '>',
            'GTEQ': '>=',
            'LT':   '<',
            'LTEQ': '<=',
            'NE':   '!='
            }

FIELDS =    {
            'CITY': 'city',
            'TOPIC': 'topics',
            'MONTH': 'month',
            'MAX_ATTENDEES': 'maxAttendees',
            }

SESSION_FIELDS = {
    'DURATION': 'duration',
    'SPEAKERS': 'speakers',
    'TYPEOFSESSION': 'typeOfSession',
    'STARTTIME': 'startTime',
    'DATE': 'date',
    'HIGHLIGHTS': 'highlights',
}

# Resource containers (defined From class with query parameters)
CONF_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeConferenceKey=messages.StringField(1),
)

CONF_POST_REQUEST = endpoints.ResourceContainer(
    ConferenceForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_GET_REQUEST = endpoints.ResourceContainer(
    message_types.VoidMessage,
    websafeSessionKey=messages.StringField(1),
)

SESSION_POST_REQUEST = endpoints.ResourceContainer(
    SessionForm,
    websafeConferenceKey=messages.StringField(1),
)

SESSION_QUERY_REQUEST = endpoints.ResourceContainer(
    ConferenceQueryForms,
    websafeConferenceKey=messages.StringField(1),
)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
@endpoints.api(name='conference', version='v1', audiences=[ANDROID_AUDIENCE],
    allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID, ANDROID_CLIENT_ID, IOS_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

# - - - Conference objects - - - - - - - - - - - - - - - - -

    def _copyConferenceToForm(self, conf, displayName):
        """Copy relevant fields from Conference to ConferenceForm."""
        cf = ConferenceForm()

        for field in cf.all_fields():
            if hasattr(conf, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(cf, field.name, str(getattr(conf, field.name)))
                else:
                    setattr(cf, field.name, getattr(conf, field.name))
            elif field.name == "websafeKey":
                setattr(cf, field.name, conf.key.urlsafe())
        if displayName:
            setattr(cf, 'organizerDisplayName', displayName)
        cf.check_initialized()
        return cf


    def _createConferenceObject(self, request):
        """Create or update Conference object, returning ConferenceForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        if not request.name:
            raise endpoints.BadRequestException("Conference 'name' field required")

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeKey']
        del data['organizerDisplayName']

        # add default values for those missing (both data model & outbound Message)
        for df in DEFAULTS:
            if data[df] in (None, []):
                data[df] = DEFAULTS[df]
                setattr(request, df, DEFAULTS[df])

        # convert dates from strings to Date objects; set month based on start_date
        if data['startDate']:
            data['startDate'] = datetime.strptime(data['startDate'][:10], "%Y-%m-%d").date()
            data['month'] = data['startDate'].month
        else:
            data['month'] = 0
        if data['endDate']:
            data['endDate'] = datetime.strptime(data['endDate'][:10], "%Y-%m-%d").date()

        # set seatsAvailable to be same as maxAttendees on creation
        if data["maxAttendees"] > 0:
            data["seatsAvailable"] = data["maxAttendees"]
        # generate Profile Key based on user ID and Conference
        # ID based on Profile key get Conference key from ID
        p_key = ndb.Key(Profile, user_id)
        c_id = Conference.allocate_ids(size=1, parent=p_key)[0]
        c_key = ndb.Key(Conference, c_id, parent=p_key)
        data['key'] = c_key
        data['organizerUserId'] = request.organizerUserId = user_id

        # create Conference, send email to organizer confirming
        # creation of Conference & return (modified) ConferenceForm
        Conference(**data).put()
        taskqueue.add(params={'email': user.email(),
            'conferenceInfo': repr(request)},
            url='/tasks/send_confirmation_email'
        )
        return request


    @ndb.transactional()
    def _updateConferenceObject(self, request):
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # copy ConferenceForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}

        # update existing conference
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Not getting all the fields, so don't create a new object; just
        # copy relevant fields from ConferenceForm to Conference object
        for field in request.all_fields():
            data = getattr(request, field.name)
            # only copy fields where we get data
            if data not in (None, []):
                # special handling for dates (convert string to Date)
                if field.name in ('startDate', 'endDate'):
                    data = datetime.strptime(data, "%Y-%m-%d").date()
                    if field.name == 'startDate':
                        conf.month = data.month
                # write to Conference object
                setattr(conf, field.name, data)
        conf.put()
        prof = ndb.Key(Profile, user_id).get()
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))


    @endpoints.method(ConferenceForm, ConferenceForm,
            path='conference',
            http_method='POST',
            name='createConference')
    def createConference(self, request):
        """Create new conference."""
        return self._createConferenceObject(request)


    @endpoints.method(CONF_POST_REQUEST, ConferenceForm,
            path='conference/{websafeConferenceKey}',
            http_method='PUT',
            name='updateConference')
    def updateConference(self, request):
        """Update conference w/provided fields & return w/updated info."""
        return self._updateConferenceObject(request)


    @endpoints.method(CONF_GET_REQUEST, ConferenceForm,
            path='conference/{websafeConferenceKey}',
            http_method='GET',
            name='getConference')
    def getConference(self, request):
        """Return requested conference (by websafeConferenceKey)."""
        # get Conference object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        prof = conf.key.parent().get()
        # return ConferenceForm
        return self._copyConferenceToForm(conf, getattr(prof, 'displayName'))


    # WHY POST instead of GET: That is because in getConferencesCreated we have a check for the user authentication and it is generally good practice to have all authentication requests sent through a POST request and not GET. That being said POST exposes just as much information as a GET in the actual network communication between the client and server but has the added advantage of not having information being visible in URL.
    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='getConferencesCreated',
            http_method='POST',
            name='getConferencesCreated')
    def getConferencesCreated(self, request):
        """Return conferences created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user
        confs = Conference.query(ancestor=ndb.Key(Profile, user_id))
        prof = ndb.Key(Profile, user_id).get()
        # return set of ConferenceForm objects per Conference
        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, getattr(prof, 'displayName')) for conf in confs]
        )


    def _getQuery(self, request):
        """Return formatted query from the submitted filters."""
        q = Conference.query()
        inequality_filter, filters = self._formatFilters(request.filters)

        # If exists, sort on inequality filter first
        if not inequality_filter:
            q = q.order(Conference.name)
        else:
            q = q.order(ndb.GenericProperty(inequality_filter))
            q = q.order(Conference.name)

        for filtr in filters:
            if filtr["field"] in ["month", "maxAttendees"]:
                filtr["value"] = int(filtr["value"])
            formatted_query = ndb.query.FilterNode(filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q


    def _formatFilters(self, filters, FIELDS=FIELDS, OPERATORS=OPERATORS):
        """Parse, check validity and format user supplied filters."""
        formatted_filters = []
        inequality_field = None

        for f in filters:
            filtr = {field.name: getattr(f, field.name) for field in f.all_fields()}

            try:
                filtr["field"] = FIELDS[filtr["field"]]
                filtr["operator"] = OPERATORS[filtr["operator"]]
            except KeyError:
                raise endpoints.BadRequestException("Filter contains invalid field or operator.")

            # Every operation except "=" is an inequality
            if filtr["operator"] != "=":
                # check if inequality operation has been used in previous filters
                # disallow the filter if inequality was performed on a different field before
                # track the field on which the inequality operation is performed
                if inequality_field and inequality_field != filtr["field"]:
                    raise endpoints.BadRequestException("Inequality filter is allowed on only one field.")
                else:
                    inequality_field = filtr["field"]

            formatted_filters.append(filtr)
        return (inequality_field, formatted_filters)

    # TODO: allow multiple inequality filter here
    # def _formatFilters(self, filters, FIELDS=FIELDS, OPERATORS=OPERATORS):
        # """Parse, check validity and format user supplied filters."""
        # formatted_filters = []
        # inequality_field = None

        # for f in filters:
        #     filtr = {field.name: getattr(f, field.name) for field in f.all_fields()}

        #     try:
        #         filtr["field"] = FIELDS[filtr["field"]]
        #         filtr["operator"] = OPERATORS[filtr["operator"]]
        #     except KeyError:
        #         raise endpoints.BadRequestException("Filter contains invalid field or operator.")

        #     # Every operation except "=" is an inequality
        #     if filtr["operator"] != "=":
        #         # check if inequality operation has been used in previous filters
        #         # disallow the filter if inequality was performed on a different field before
        #         # track the field on which the inequality operation is performed
        #         if inequality_field and inequality_field != filtr["field"]:
        #             raise endpoints.BadRequestException("Inequality filter is allowed on only one field.")
        #         else:
        #             inequality_field = filtr["field"]

        #     formatted_filters.append(filtr)
        # return (inequality_field, formatted_filters)


    @endpoints.method(ConferenceQueryForms, ConferenceForms,
            path='queryConferences',
            http_method='POST',
            name='queryConferences')
    def queryConferences(self, request):
        """Query for conferences."""
        conferences = self._getQuery(request)

        # need to fetch organiser displayName from profiles
        # get all keys and use get_multi for speed
        organisers = [(ndb.Key(Profile, conf.organizerUserId)) for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            if profile:
                names[profile.key.id()] = profile.displayName

        # return individual ConferenceForm object per Conference
        return ConferenceForms(
                items=[self._copyConferenceToForm(conf, names[conf.organizerUserId]) for conf in conferences]
        )


# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from Profile to ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf


    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get()
        # create new Profile if not there
        if not profile:
            profile = Profile(
                key = p_key,
                displayName = user.nickname(),
                mainEmail= user.email(),
                teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
            )
            profile.put()

        return profile      # return Profile


    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        #if field == 'teeShirtSize':
                        #    setattr(prof, field, str(val).upper())
                        #else:
                        #    setattr(prof, field, val)
                        prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)


    @endpoints.method(message_types.VoidMessage, ProfileForm,
            path='profile',
            http_method='GET',
            name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()


    @endpoints.method(ProfileMiniForm, ProfileForm,
            path='profile',
            http_method='POST',
            name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)


# - - - Announcements - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cacheAnnouncement():
        """Create Announcement & assign to memcache; used by
        memcache cron job & putAnnouncement().
        """
        confs = Conference.query(ndb.AND(
            Conference.seatsAvailable <= 5,
            Conference.seatsAvailable > 0)
        ).fetch(projection=[Conference.name])

        if confs:
            # If there are almost sold out conferences,
            # format announcement and set it in memcache
            announcement = ANNOUNCEMENT_TPL % (
                ', '.join(conf.name for conf in confs))
            memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
        else:
            # If there are no sold out conferences,
            # delete the memcache announcements entry
            announcement = ""
            memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

        return announcement


    @endpoints.method(message_types.VoidMessage, StringMessage,
            path='conference/announcement/get',
            http_method='GET',
            name='getAnnouncement')
    def getAnnouncement(self, request):
        """Return Announcement from memcache."""
        return StringMessage(data=memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY) or "")


# - - - Registration - - - - - - - - - - - - - - - - - - - -

    @ndb.transactional(xg=True)
    def _conferenceRegistration(self, request, reg=True):
        """Register or unregister user for selected conference."""
        retval = None
        prof = self._getProfileFromUser() # get user Profile

        # check if conf exists given websafeConfKey
        # get conference; check that it exists
        wsck = request.websafeConferenceKey
        conf = ndb.Key(urlsafe=wsck).get()
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % wsck)

        # register
        if reg:
            # check if user already registered otherwise add
            if wsck in prof.conferenceKeysToAttend:
                raise ConflictException(
                    "You have already registered for this conference")

            # check if seats avail
            if conf.seatsAvailable <= 0:
                raise ConflictException(
                    "There are no seats available.")

            # register user, take away one seat
            prof.conferenceKeysToAttend.append(wsck)
            conf.seatsAvailable -= 1
            retval = True

        # unregister
        else:
            # check if user already registered
            if wsck in prof.conferenceKeysToAttend:

                # unregister user, add back one seat
                prof.conferenceKeysToAttend.remove(wsck)
                conf.seatsAvailable += 1
                retval = True
            else:
                retval = False

        # write things back to the datastore & return
        prof.put()
        conf.put()
        return BooleanMessage(data=retval)


    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='conferences/attending',
            http_method='GET',
            name='getConferencesToAttend')
    def getConferencesToAttend(self, request):
        """Get list of conferences that user has registered for."""
        prof = self._getProfileFromUser() # get user Profile
        conf_keys = [ndb.Key(urlsafe=wsck) for wsck in prof.conferenceKeysToAttend]
        conferences = ndb.get_multi(conf_keys)

        # get organizers
        organisers = [ndb.Key(Profile, conf.organizerUserId) for conf in conferences]
        profiles = ndb.get_multi(organisers)

        # put display names in a dict for easier fetching
        names = {}
        for profile in profiles:
            names[profile.key.id()] = profile.displayName

        # return set of ConferenceForm objects per Conference
        return ConferenceForms(items=[self._copyConferenceToForm(conf, names[conf.organizerUserId]) for conf in conferences])


    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='POST',
            name='registerForConference')
    def registerForConference(self, request):
        """Register user for selected conference."""
        return self._conferenceRegistration(request)


    @endpoints.method(CONF_GET_REQUEST, BooleanMessage,
            path='conference/{websafeConferenceKey}',
            http_method='DELETE',
            name='unregisterFromConference')
    def unregisterFromConference(self, request):
        """Unregister user for selected conference."""
        return self._conferenceRegistration(request, reg=False)


    @endpoints.method(message_types.VoidMessage, ConferenceForms,
            path='filterPlayground',
            http_method='GET',
            name='filterPlayground')
    def filterPlayground(self, request):
        """Filter Playground"""
        q = Conference.query()
        # field = "city"
        # operator = "="
        # value = "London"
        # f = ndb.query.FilterNode(field, operator, value)
        # q = q.filter(f)
        q = q.filter(Conference.city=="London")
        q = q.filter(Conference.topics=="Medical Innovations")
        q = q.filter(Conference.month==6)

        return ConferenceForms(
            items=[self._copyConferenceToForm(conf, "") for conf in q]
        )

# - - - Session  - - - - - - - - - - - - - - - - -

    def _copySessionToForm(self, session, conferenceName):
        """Copy relevant fields from Session to SessionForm."""
        sf = SessionForm()
        for field in sf.all_fields():
            if hasattr(session, field.name):
                if field.name == 'typeOfSession':
                    # convert type of session string to Enum
                    setattr(sf, field.name, getattr(SessionType, getattr(session, field.name)))
                # convert Date to date string; just copy others
                elif field.name.endswith('date'):
                    setattr(sf, field.name, str(getattr(session, field.name)))
                elif field.name.endswith('Time'):
                    # TODO: handle 24 hrs time
                    setattr(sf, field.name, str(getattr(session, field.name)))
                else:
                    setattr(sf, field.name, getattr(session, field.name))
            elif field.name == "websafeKey":
                setattr(sf, field.name, session.key.urlsafe())

        if conferenceName:
            setattr(sf, 'conferenceName', conferenceName)
        sf.check_initialized()
        return sf


    def _createSessionObject(self, request):
        """Create or update Session object, returning SessionForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        # Populate session fields
        if not request.name:
            raise endpoints.BadRequestException("Session 'name' field required")

        # copy SessionForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeConferenceKey']
        del data['conferenceName']
        del data['websafeKey']

        # add default values for those missing (both data model & outbound Message)
        for df in SESSION_DEFAULTS:
            if data[df] in (None, []):
                data[df] = SESSION_DEFAULTS[df]
                setattr(request, df, SESSION_DEFAULTS[df])

        # convert dates from strings to Date objects; set month based on start_date
        if data['date']:
            data['date'] = datetime.strptime(data['date'][:10], "%Y-%m-%d").date()

        if data['startTime']:
            data['startTime'] = datetime.strptime(data['startTime'][:5], "%H:%M").time()

        if not data['typeOfSession']:
            data['typeOfSession'] = str(SessionType.NOT_SPECIFIED)
        else:
            data['typeOfSession'] = str(data['typeOfSession'])

        # allocate
        c_key = conf.key
        s_id = Session.allocate_ids(size=1, parent=c_key)[0]
        s_key = ndb.Key(Session, s_id, parent=c_key)

        data['key'] = s_key
        data['conferenceKey'] = request.websafeConferenceKey

        # create session
        session = Session(**data)
        session.put()

        # email organizer, confirming creation of session
        taskqueue.add(params={'email': user.email(),
            'conferenceSessionInfo': repr(data)},
            url='/tasks/send_confirmation_email'
        )
        taskqueue.add(params={'websafeSessionKey': s_key.urlsafe()},
            url='/tasks/set_featured_speaker'
        )

        return self._copySessionToForm(session, getattr(conf, 'name'))


    @endpoints.method(SESSION_POST_REQUEST, SessionForm,
            path='conference/{websafeConferenceKey}/session',
            http_method='POST',
            name='createSession')
    def createSession(self, request):
        """Create new Session."""
        return self._createSessionObject(request)


    @endpoints.method(CONF_GET_REQUEST, SessionForms,
            path='conference/{websafeConferenceKey}/sessions',
            http_method='GET', name='getConferenceSessions')
    def getConferenceSessions(self, request):
        """Return requested Sessions (by websafeConferenceKey)."""
        # get Session object from request; bail if not found
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        sessions = Session.query(ancestor=conf.key)
        return SessionForms(items = [self._copySessionToForm(session, getattr(conf, 'name')) for session in sessions])

    # Implemented an additional method to quickly delete all sessions in a conference
    @endpoints.method(CONF_GET_REQUEST, message_types.VoidMessage,
            path='conference/{websafeConferenceKey}/sessions',
            http_method='DELETE', name='deleteAllConferenceSessions')
    def deleteAllConferenceSessions(self, request):
        """Delete all sessions (by websafeConferenceKey)."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        user_id = getUserId(user)

        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)

        # check that user is owner
        if user_id != conf.organizerUserId:
            raise endpoints.ForbiddenException(
                'Only the owner can update the conference.')

        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        sessions = Session.query(ancestor=conf.key)
        for session in sessions:
            session.key.delete()
        return message_types.VoidMessage()


    @endpoints.method(SESSION_QUERY_REQUEST, SessionForms,
            path='conference/{websafeConferenceKey}/sessions',
            http_method='POST', name='getConferenceSessionsByType')
    def getConferenceSessionsByType(self, request):
        """Return requested Sessions (by websafeConferenceKey, typeOfSession)."""
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        sessions = self._getSessionQuery(request, ancestor=conf.key, required_fields=['typeOfSession'])
        return SessionForms(items = [self._copySessionToForm(session, getattr(conf, 'name')) for session in sessions])

    # reuse conference query form in session queries as well
    @endpoints.method(ConferenceQueryForms, SessionForms,
        path='session',
        http_method='GET', name='getSessionsBySpeaker')
    def getSessionsBySpeaker(self, request):
        """Return all sessions with a speaker (by Speaker Name)"""
        sessions = self._getSessionQuery(request, ancestor=None, required_fields=['speakers'])

        # get each session's parent conference name
        conf_keys = [ndb.Key(urlsafe=session.conferenceKey) for session in sessions]
        confs = ndb.get_multi(conf_keys)
        conf_names = [conf.name for conf in confs]

        return SessionForms(items = [self._copySessionToForm(session, conf_name) for (session, conf_name) in zip(sessions, conf_names)])


# - - - Session Wishlist  - - - - - - - - - - - - - - - - -

    def _sessionWishList(self, request, add=True):
        """Add or remove session from a user's wishlist,
        if user attends the conference"""
        retval = None
        prof = self._getProfileFromUser() # get user Profile

        s_key = request.websafeSessionKey
        session = ndb.Key(urlsafe = s_key).get()
        conf_key = ndb.Key(urlsafe=session.conferenceKey)

        if not session:
            raise endpoints.NotFoundException(
                'No session found with key: %s' % s_key)

        # add to wishlist
        if add:
            if s_key in prof.sessionKeysToAttend:
                raise ConflictException(
                    "You have already added this session in your wishlist")

            if session.conferenceKey not in prof.conferenceKeysToAttend:
                raise endpoints.ForbiddenException(
                    'You need to register for the conference before adding a session to your wishlist.')

            prof.sessionKeysToAttend.append(s_key)
            retval = True

        # remove from wishlist
        else:
            if s_key in prof.sessionKeysToAttend:
                prof.sessionKeysToAttend.remove(s_key)
                retval = True
            else:
                retval = False

        prof.put()
        return BooleanMessage(data=retval)

    @endpoints.method(SESSION_GET_REQUEST, BooleanMessage,
        path='session/{websafeSessionKey}',
        http_method="POST",
        name="addSessionToWishlist")
    def addSessionToWishList(self, request):
        """add session to user's wishlist"""
        return self._sessionWishList(request, add=True)

    @endpoints.method(SESSION_GET_REQUEST, BooleanMessage,
        path='session/{websafeSessionKey}',
        http_method="DELETE",
        name="removeSessionFromWishlist")
    def removeSessionFromWishList(self, request):
        """remove session from user's wishlist"""
        return self._sessionWishList(request, add=False)

    @endpoints.method(CONF_GET_REQUEST, SessionForms,
        path='conference/{websafeConferenceKey}/wishlist',
        http_method="POST",
        name="getSessionsInWishlist")
    def getSessionsInWishlist(self, request):
        """Get all sessions in user's wishlist in a conference"""
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        prof = self._getProfileFromUser()
        s_keys = [ndb.Key(urlsafe=s_key) for s_key in prof.sessionKeysToAttend]
        sessions = [session
                    for session in ndb.get_multi(s_keys)
                    if session.conferenceKey == request.websafeConferenceKey]

        # return set of ConferenceForm objects per Conference
        return SessionForms(items = [self._copySessionToForm(session, getattr(conf, 'name')) for session in sessions])

# - - - Session Query  - - - - - - - - - - - - - - - - -
    def _getSessionQuery(self, request, ancestor = None, required_fields = []):
        """Return formatted query from the submitted filters."""
        if ancestor:
            q = Session.query(ancestor=ancestor)
        else:
            q = Session.query()

        inequality_filter, filters = self._formatFilters(request.filters, SESSION_FIELDS, OPERATORS)
        # all required_fields must appear in filters field
        included_fields = [f['field'] for f in filters]
        missing_fields = [rf for rf in required_fields if rf not in included_fields]
        if missing_fields:
            raise endpoints.BadRequestException("Session '%s' field required" % "', '".join(missing_fields))

        # If exists, sort on inequality filter first
        if inequality_filter:
            q = q.order(ndb.GenericProperty(inequality_filter))
        q = q.order(Session.name)

        for filtr in filters:
            if filtr["field"] in ["duration"]:
                filtr["value"] = int(filtr["value"])
            elif filtr["field"] in ["highlights"]:
                filtr["value"] = str(filtr["value"]).lower() == 'true'
            formatted_query = ndb.query.FilterNode(filtr["field"], filtr["operator"], filtr["value"])
            q = q.filter(formatted_query)
        return q

    @endpoints.method(SESSION_QUERY_REQUEST, SessionForms,
            path='conference/{websafeConferenceKey}/session/query',
            http_method='POST', name='queryConferenceSessions')
    def queryConferenceSessions(self, request):
        """Return requested Sessions (by websafeConferenceKey, filters)."""
        conf = ndb.Key(urlsafe=request.websafeConferenceKey).get()
        # check that conference exists
        if not conf:
            raise endpoints.NotFoundException(
                'No conference found with key: %s' % request.websafeConferenceKey)
        sessions = self._getSessionQuery(request, ancestor=conf.key)
        return SessionForms(items = [self._copySessionToForm(session, getattr(conf, 'name')) for session in sessions])

    @endpoints.method(message_types.VoidMessage, SessionForms,
            path='filterSessionPlayground',
            http_method='GET',
            name='filterSessionPlayground')
    def filterSessionPlayground(self, request):
        """Filter Playground"""
        q = Session.query()
        # field = "city"
        # operator = "="
        # value = "London"
        # f = ndb.query.FilterNode(field, operator, value)
        # q = q.filter(f)
        q = q.filter(Session.typeOfSession!="Workshop")
        latest_start = datetime.strptime('15:00', "%H:%M").time()
        q = q.filter(Session.startTime < latest_start)

        return SessionForms(
            items=[self._copySessionToForm(s, "") for s in q]
        )
# - - - Featured speaker - - - - - - - - - - - - - - - - - - - -

    @staticmethod
    def _cacheFeaturedSpeakers(websafeSessionKey):
        """Create Featured Speakers & assign to memcache; used by
        memcache cron job & SetFeaturedSpeakerHandler().
        """
        session = ndb.Key(urlsafe=websafeSessionKey).get()
        c_key = ndb.Key(urlsafe=session.conferenceKey)
        c_name = c_key.get().name
        # set featured speaker, if any
        for speaker in session.speakers:
            sessions = Session.query(ancestor=c_key).filter(Session.speakers == speaker)
            # if speak at > 1 sessions, the speaker is featured
            if sessions and sessions.count() > 1:
                # add featured speaker to memcache
                featured_speakers = memcache.get(MEMCACHE_FEATUREDSPEAKER_KEY)
                # can't use defaultdict(lambda: defaultdict(str)) since function can't be serialized
                if featured_speakers is None:
                    featured_speakers = {}
                if str(session.conferenceKey) not in featured_speakers.keys():
                    featured_speakers[str(session.conferenceKey)] = defaultdict(str)
                featured_speakers[str(session.conferenceKey)][speaker] = FEATURED_SPEAKER_TPL %(speaker, sessions.count(), c_name, ', '.join([s.name for s in sessions]))
                memcache.set(MEMCACHE_FEATUREDSPEAKER_KEY, featured_speakers)
        return featured_speakers

#
    @endpoints.method(CONF_GET_REQUEST, StringMessages,
            path='conference/{websafeConferenceKey}/getFeaturedSpeaker',
            http_method='GET',
            name='getFeaturedSpeaker')
    def getFeaturedSpeaker(self, request):
        """Return Announcement from memcache."""
        featured_speakers = memcache.get(MEMCACHE_FEATUREDSPEAKER_KEY)
        fs = ['']
        if featured_speakers:
            fs = featured_speakers.get(str(request.websafeConferenceKey), {}).values()
        return StringMessages(data=fs)


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
api = endpoints.api_server([ConferenceApi]) # register API

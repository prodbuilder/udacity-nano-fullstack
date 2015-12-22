# App Engine application for the Udacity training course `Conference App`.

**Contents**
<!-- MarkdownTOC depth=4-->

- Setup Instructions
- Tasks
  - 1. Sessions and speakers
  - 2. Session wishlist
  - 3. Work on indexes and queries
  - 4. Add a task

<!-- /MarkdownTOC -->


# Setup Instructions
1. Run the app with the devserver using `dev_appserver.py app.yaml --port=10080`, (or whatever port that you have available) and ensure it's running by visiting your local server's address (by default [localhost:10080][5].)
2. Or visit [https://apis-explorer.appspot.com/apis-explorer/?base=https://confapp-1157.appspot.com/_ah/api#p/conference/v1/] to check the deployed version.

# Tasks
## 1. Sessions and speakers
`Session` is implemented as new entity in datastore, along side `Conference` and `Profile`. It includes the following properties:
```
    - conferenceKey   
    - name            
    - highlights      
    - speakers        
    - duration        
    - date            
    - startTime       
    - typeOfSession   
```

The `spearkers` are list of strings (`ndb.StringProperty(repeated=True)`) representing the speaker names. 

In addition, `hightlights` is a boolean property, duration is integer representing duration in minutes; `date` is `ndb.DateProperty()` and `startTime` is `ndb.TimeProperty()`. `typeOfSession` is a string property, and its allowed values are controlled by the inbound form, which sets the `typeOfSession` from defined `EnumField`. 

The outbound `SessionForm` also stores `conferenceName` for ease of displaying relevant information. 

### endpoint methods
- `getConferenceSessions` retrieves all sessions of a conference, by `websafeConferenceKey`, by performing an ancester query
- `createSession` for a conference allows creating a session that the user organizes
- `deleteAllConferenceSessions` is a convenience method that deletes all sessions in a conference, by ancester query.


## 2. Session wishlist

### endpoint methods
- `addSessionToWishlist` and `removeSessionFromWishlist` both utilize `_sessionWishlist` method, and append or remove a session to the list of session keys stored in a property `sessionKeysToAttend` in `Profile` entity.
- `getSessionsInWishlist` simply retrieves multiple entries based on the session keys from the user's `sessionKeysToAttend` property.

## 3. Work on indexes and queries

### endpoint methods
- `getConferenceSessionsByType` and `getSessionsBySpeaker` both utilize a more general `queryConferenceSessions` method to perform queries, with or without ancester query, and additional filters.

### Additional queries
Additional queries can be conducted in the same way re-using the `ConferenceQueryForms` provided in starter code, in `queryConferenceSessions`. 

This method supports a list of filters. In fact, both methods `getSessionsBySpeaker(speaker)` and `getConferenceSessionsByType(websafeConferenceKey, typeOfSession)` were implemented using the same method, while only querying on one required field -- `speaker` for the former and `typeOfSession` for the latter. Having `websafeConferenceKey` simply takes an ancestor query.

- Find highlighted Lectures in a conference
This uses a combined filter of `typeOfSession` with value `Lecture` and `highlights` with value `true`

- Keynote sessions that include a certain speaker in a conference
This uses a combined filter of `typeOfSession` with value `Keynote` and `speakers` with a given name. 

### Indices
Created by performing queries on test instance. Here are the ones used for methods implemented in this exercise:

For `getConferenceSessions`:
```
- kind: Session
  ancestor: yes
  properties:
  - name: name
```

For `getSessionsBySpeaker(speaker)`:
```
- kind: Session
  properties:
  - name: speakers
  - name: name
```

For `queryConferenceSessions`:
```
- kind: Session
  ancestor: yes
  properties:
  - name: typeOfSession
  - name: name
```

For `highlighted lectures in a conference`: 
```
- kind: Session
  ancestor: yes
  properties:
  - name: highlights
  - name: typeOfSession
  - name: name
```

For `keynotes spoken by a certain person in a conferences`:
```
- kind: Session
  ancestor: yes
  properties:
  - name: speakers
  - name: typeOfSession
  - name: name
```


### Get around multiple inequality filters on different properties
Let’s say that you don't like workshops and you don't like sessions after 7 pm. How would you handle a query for all non-workshop sessions before 7 pm? What is the problem for implementing this query? What ways to solve it did you think of?

Google Appengine datastore does not allow multiple inequality filters on two different fields. To get around this, here are a few potential solutions:

1. considering we have only a fairly small number of Session types, we can explicityly query for the types other than `Workshop` using `ndb.OR`

2. We can retrieve all the sessions that satisfy the start time constraint, and filter on workshop from within python; or vice versa, retrive all workshops and then filter on start time in python. Depending on how many sessions there are in a typical conference, this can cause unnecessary reads from datastore.

## 4. Add a task
When a new session is created, a new task is added to the task queue, to determine whether or not there are new featured speakers for a conference. If so, we will store the information in the corresponding values in memcache identified by `MEMCACHE_FEATUREDSPEAKER_KEY`, which is implemented as a dictionary, where keys are `websafeConferenceKey`s and value is again a dictionary of (speaker, info), where the info stores formatted string of conference name, speaker name and session names.


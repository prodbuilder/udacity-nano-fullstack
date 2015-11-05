#!/usr/bin/env python
#
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2

# helper functions to read and update from DB
def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    return psycopg2.connect("dbname=tournament")

def update_with(query, arg=None):
    con = connect()
    cur = con.cursor()
    if arg:
        cur.execute(query, arg)
    else:
        cur.execute(query)
    con.commit()
    con.close()

def get_with(query):
    con = connect()
    cur = con.cursor()
    cur.execute(query)
    con.commit()
    n = cur.fetchall()
    con.close()
    return n


def deleteMatches():
    """Remove all the match records from the database."""
    query = "DELETE FROM matches;"
    update_with(query)


def deletePlayers():
    """Remove all the player records from the database."""
    query = "DELETE FROM players;"
    update_with(query)


def countPlayers():
    """Returns the number of players currently registered."""
    query = "SELECT COUNT(*) FROM players LIMIT 1;"
    return get_with(query)[0][0]

def registerPlayer(name):
    """Adds a player to the tournament database.

    The database assigns a unique serial id number for the player.  (This
    should be handled by your SQL database schema, not in your Python code.)

    Args:
      name: the player's full name (need not be unique).
    """
    query = "INSERT INTO players (name) VALUES (%s);"
    update_with(query, (name, ))


def playerStandings():
    """Returns a list of the players and their win records, sorted by wins.

    The first entry in the list should be the player in first place, or a player
    tied for first place if there is currently a tie.

    Returns:
      A list of tuples, each of which contains (id, name, wins, matches):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        matches: the number of matches the player has played
    """
    query = "SELECT id, name, wins, matches from standings;"
    return get_with(query)


def reportMatch(winner, loser):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
    """
    query = "INSERT INTO matches (winner, loser, score) VALUES (%s, %s, %s)"
    update_with(query, (winner, loser, 1))


def swissPairings():
    """Returns a list of pairs of players for the next round of a match.

    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings.

    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    query = "SELECT * from pairings;"
    return get_with(query)


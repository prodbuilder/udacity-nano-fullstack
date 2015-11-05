This app will implement a Swiss-system tournament, in a single tournament, with even number of players.

# Quick start

Download the code from github or clone the [repo](https://github.com/prodbuilder/udacity-nano-fullstack)

## What's included
```sh
README.md
tournament.py
tournament.sql
tournament_test.py
```

## Run the program locally
`Vagrant ssh` to udacity VM cloned from [here](https://github.com/udacity/fullstack-nanodegree-vm).

### 1. Create database
First go to `psql`
```sh
cd /vagrant/tournament
psql
```

Then simply run the `sql` commands to create database `tournament` and relevant tables.
```psql
\i tournament.sql
```

### 2. Test implementation
```sh
cd /vagrant/tournament
python tournament_test.py
```

The correct implementation will show
```sh
1. Old matches can be deleted.
2. Player records can be deleted.
3. After deleting, countPlayers() returns zero.
4. After registering a player, countPlayers() returns 1.
5. Players can be registered and deleted.
6. Newly registered players appear in the standings with no matches.
7. After a match, players have updated standings.
8. After one match, players with one win are paired.
Success!  All tests pass!
```
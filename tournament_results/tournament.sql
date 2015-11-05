-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.

DROP DATABASE IF EXISTS tournament;

CREATE DATABASE tournament;

-- connect to newly created empty database
\c tournament;

CREATE TABLE players (
    id     SERIAL PRIMARY KEY,
    name   VARCHAR(100) NOT NULL
    CONSTRAINT name_not_empty CHECK (name <> '')
);

CREATE TABLE matches (
    id       SERIAL PRIMARY KEY,
    winner         INTEGER REFERENCES players(id),
    loser          INTEGER REFERENCES players(id),
    score          INTEGER
    CONSTRAINT allowed_scores CHECK ( score in (0, 1))
);


-- standings table for each play,
-- include rank, wins, loses, draws (if any), matches
CREATE VIEW standings AS
    WITH s AS(
        SELECT players.id, players.name,
            SUM(CASE WHEN w.score = 1 THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN l.score = 1 THEN 1 ELSE 0 END) AS loses,
            SUM(CASE WHEN w.score = 0 THEN 1 ELSE 0 END) AS draws,
            SUM(CASE WHEN w.score = 1 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN l.score = 1 THEN 1 ELSE 0 END) +
            SUM(CASE WHEN w.score = 0 THEN 1 ELSE 0 END) AS matches
            FROM players
            LEFT JOIN matches w ON players.id = w.winner
            LEFT JOIN matches l ON players.id = l.loser
            GROUP BY players.id
            ORDER BY wins DESC)
    SELECT ROW_NUMBER() OVER (ORDER BY wins DESC NULLS LAST) AS rank,
           s.*
    FROM s;

-- pairings take odd and even rows from sorted standings view
-- and match player with (2k-1)_th standing with (2k)_th standing
CREATE VIEW pairings AS
    WITH
      a AS (
        SELECT rank, id, name
        FROM standings
        WHERE mod(rank, 2) = 0 ),
      b AS (
        SELECT rank, id, name
        FROM standings
        WHERE mod(rank, 2) = 1 )
    SELECT
        a.id AS id1, a.name AS name1,
        b.id AS id2, b.name AS name2
        FROM a JOIN b
        ON a.rank - 1 = b.rank;

# Store movie information in a class
# use fresh_tomatos.py to display a list of movies in a html page

import fresh_tomatos

class Movie:
    """
    The Movie class stores relevant properties of a movie, such as
    its title, box art url, youtube trailer url, etc.
    """
    def __init__(self, title, poster_image_url, trailer_youtube_url, year, director):
        self.title = title
        self.poster_image_url = poster_image_url
        self.trailer_youtube_url = trailer_youtube_url
        self.year = year
        self.director = director


def load_movies():
    """
    Store my favorite movies in a list, and output this list
    """
    minions = Movie(
        'Minions',
        'https://upload.wikimedia.org/wikipedia/en/3/3d/Minions_poster.jpg',
        'https://www.youtube.com/watch?v=P9-FCC6I7u0',
        2015,
        'Pierre Coffin, Kyle Balda')

    spirit = Movie(
        'Spirit: Stallion of the Cimarron',
        'https://upload.wikimedia.org/wikipedia/en/3/3b/Spirit_Stallion_of_the_Cimarron_poster.jpg',
        'https://www.youtube.com/watch?v=8Nj4_L3Vbu0',
        2002,
        'Kelly Asbury, Lorna Cook')

    madagascar = Movie(
        'Madagascar',
        'https://upload.wikimedia.org/wikipedia/en/3/36/Madagascar_Theatrical_Poster.jpg',
        'https://www.youtube.com/watch?v=hdcTmpvDO0I',
        2005,
        'Tom McGrath, Eric Darnell')

    return [minions, spirit, madagascar]


def main():
    fav_movies = load_movies()
    fresh_tomatos.open_movies_page(fav_movies)

if __name__ == '__main__':
    main()


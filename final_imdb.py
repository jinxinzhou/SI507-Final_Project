###############################################
# name: Jinxin Zhou ###########################
# unique name: jinxinz ########################
###############################################

import sqlite3
import requests
from bs4 import BeautifulSoup
import os
import json
import plotly.graph_objs as go
from flask import Flask, render_template,request

CACHE_FILE_NAME = "imdb_cache.json"
BASE_URL = "https://www.imdb.com"
DATABASE_FILE = "imdb.sqlite"

class Movie():
    def __init__(self, name=None, rank=None, category=None, length=None, genre=None, release_date=None, release_country=None,
                 rating=None, director=None, stars=None, image=None):#, relevant_movies=None):
        """Initiate the movie instance
        Parameters
        ----------
        name: string

        rank: int

        category: string
            One movie may have multiple categories, but treat all of them as one string

        length: string
            Input is formatted like "2h 31min" and it will be transformed into minutes.

        genre: string

        release-date: string
            Input is formatted like "day month year" and that will be transformed into format like "2012-10-01"

        release-country: string

        rating: float

        stars: dictionary
            A dictionary whose keys are the star names and values are their corresponding url.

        image: string
            A string corresponds to the url of the image of the movie.
        """
        self.name = name
        self.rank = rank
        self.category = category
        self.length = length
        self.genre = genre
        self.release_date = self.transform_date(release_date)
        self.release_country = release_country
        self.rating = rating
        self.director = director
        self.stars = stars
        self.image = image

    def info(self):
        """Return the information of the movie
        Parameters
        ----------
        None

        Returns
        -------
        info: string
        """
        info = '''Name: {name}
        Rank: {rank}                Rating:{rating}
        {genre} | {length} mins | {category} | {release_date} | {release_country}
        Director:{diretor}
        Image: {image}
        '''.format(name=self.name, rank=self.rank, rating=self.rating, genre=self.genre, length=self.length, category=" ".join(self.category),
        release_date=self.release_date, release_country=self.release_country, director=list(self.director.keys())[0], image=self.image)

        return info

    def transform_length(self, original_length):
        """Transform the length from hour-minutes format into minutes format.
        """
        length = 0
        original_length_list = original_length.split(" ")
        for l in original_length_list:
            if 'h' in l:
                length += 60*int(l[:-1])
            elif 'min' in l:
                length += int(l[:-3])
        return length

    def transform_date(self, original_date):
        """Transform the date from day month year formate into year-month-day format.
        """
        Monthes = {"January":"01", "February":"02", "March":"03", "April":"04",
                    "May":"05", "June":"06", "July":"07", "August":"08",
                    "September":"09", "October":"10", "November":"11", "December":"12"}
        original_date_list = original_date.split(" ")
        if len(original_date_list) == 2:
            month = Monthes[original_date_list[0]]
            year = original_date_list[-1]
            date = year + "-" + month
        else:
            day = original_date_list[0]
            month = Monthes[original_date_list[1]]
            year = original_date_list[-1]

            if len(day) < 2:
                day = "0"+day
            date = year + "-" + month + "-" + day

        return date

def load_cache():
    """Load cache from path

    Parameters
    ----------
    None

    Returns
    -------
    dict: cache
    """
    try:
        cache_file = open(CACHE_FILE_NAME, 'r')
        cache_file_content = cache_file.read()
        cache = json.loads(cache_file_content)
        cache_file.close()
    except:
        cache = {}

    return cache

def save_cache(cache):
    """Save cache to path

    Parameters
    ----------
    cache: dictionary

    Returns
    ------
    None
    """
    cache_file = open(CACHE_FILE_NAME, 'w')
    content_to_write = json.dumps(cache)
    cache_file.write(content_to_write)
    cache_file.close()

def build_movie_url_dict(route_path):
    """Scrape top ranked movies urls

    Parameters
    ----------
    route_path :string
        route url to the movie list page

    Returns
    -------
    movie_url_dictionary: dictionary
        A dictionary whose keys are movie names and values are movie page urls
    """
    base_url = BASE_URL

    cache = load_cache()
    movie_url_dict = {}

    if base_url + route_path in cache:
        print('Using Cache')
        movie_url_dict = cache[base_url+route_path]
    else:
        print('Fetching')
        response = requests.get(base_url+route_path)
        if response.status_code == 200:
            html = response.text
            soup = BeautifulSoup(html, 'lxml')
            movies = soup.find('tbody', class_='lister-list')
            movies = movies.find_all('td', class_ = 'titleColumn')
            for i, item in enumerate(movies):
                title_info = item.find('a')
                movie_url_dict[title_info.text.strip(' ')] = base_url+title_info['href']
        cache[base_url+route_path] = movie_url_dict
        save_cache(cache)

    return movie_url_dict

def build_movie_instances(movie_url):
    """Create movie instance from the beautiful soup

    Parameters
    ----------
    movie_url: string
        url to the movie page

    Returns
    -------
    Movie: instance of Movie class.
    """
    cache = load_cache()

    if movie_url in cache:
        print('Using cahce')
        soup = BeautifulSoup(cache[movie_url], 'html.parser')
    else:
        print('Fetching')
        resp = requests.get(movie_url)
        soup = BeautifulSoup(resp.text, 'lxml')
        cache[movie_url] = resp.text
        save_cache(cache)

    name = soup.find('div', class_='title_wrapper').find('h1').get_text(strip=True).split('(')[0]
    rank_str = soup.find('div', class_='article highlighted', id='titleAwardsRanks').find('strong').get_text(strip=True)
    if rank_str.startswith('Top Rated Movies'):
        rank = int(rank_str.split('#')[-1])
    else:
        rank = 'N/A'
    sub_info = soup.find('div',class_='subtext').get_text(strip=True).split('|')
    if len(sub_info) <= 3:
        genre = 'No Rated'
    else:
        genre = sub_info[-4]
    length = sub_info[-3]
    category = sub_info[-2].split(',')
    release_date = sub_info[-1].split('(')[0].strip(' ')
    release_country = sub_info[-1].split('(')[-1].strip(')')

    rating = float(soup.find('span', itemprop='ratingValue').get_text(strip=True))
    people = soup.find_all('div', class_='credit_summary_item')
    director_info=people[0].find('a')
    director = {director_info.get_text(strip=True):BASE_URL+director_info['href']}
    stars_info = people[2].find_all('a')
    stars={}
    for star in stars_info[:-1]:    # ignore 'See full cast&crew' link
        stars[star.get_text(strip=True)]=BASE_URL+star['href']

    image_url=BASE_URL+soup.find('div', class_='poster').find('a')['href']
    if image_url in cache:
        print('Using Cache')
        image = cache[image_url]
    else:
        print('Fetching')
        resp_image = requests.get(image_url)
        soup_image = BeautifulSoup(resp_image.text, 'lxml')
        image = soup_image.find('meta',property='twitter:image').attrs['content']
        cache[image_url] = image
        save_cache(cache)

    return Movie(name=name, rank=rank, category=category, length=length, genre=genre, release_date=release_date, release_country=release_country,
                 rating=rating, director=director, stars=stars, image=image)

def get_director_knownfor(director_page_url):
    """Get director's famous movies

    Parameters
    ----------
    director_page_url: string

    Returns
    -------
    dir_poster: string
        source url to director's poster

    knowfor: dictionary
        A dictionary whose keys are director name and values are url of his page
    """

    cache= load_cache()
    if director_page_url in cache:
        print('Using cache')
        soup = BeautifulSoup(cache[director_page_url], 'html.parser')
    else:
        print('Fetching')
        resp = requests.get(director_page_url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        cache[director_page_url] = resp.text
        save_cache(cache)

    knownfor = {}
    dir_poster = soup.find('img', id='name-poster')['src']
    knownfor_info = soup.find('div', id='knownfor').find_all('div', class_='knownfor-title')
    for work_source in knownfor_info:
        work_info = work_source.find('div', class_='knownfor-title-role').find('a')
        poster_source = work_source.find('div', class_='uc-add-wl-widget-container').find('img')['src']
        knownfor[work_info.get_text(strip=True)]=(BASE_URL+work_info['href'], poster_source)

    return dir_poster, knownfor

def get_top_ranked_movies(movie_url_dict, top_num=250):
    """Get top ranked movie instances from the web

    Parameters
    ----------
    movie_url_dict: dictionary

    top_num: int
        The number of top movies you want to get

    Returns
    -------
    top_movies: list
        A list a movie instances
    """
    top_movies = []
    limit_num = min(len(movie_url_dict), top_num)
    for i, movie in enumerate(movie_url_dict):
        if i >= limit_num:
            break
        else:
            top_movies.append(build_movie_instances(movie_url_dict[movie]))
    return top_movies

def get_directors_from_movies(movie_instances):
    '''get directors from a list of movie instances

    Parameters
    ----------
    movie_instances: list

    Retuens
    -------
    directors: list
        a list director page urls
    '''
    directors = []
    for movie in movie_instances:
        if tuple(movie.director.items())[0] in directors:
            continue
        else:
            directors.append(tuple(movie.director.items())[0])
    return directors


#################################################################
# database part
#################################################################

def create_sql_tables():
    '''create movie and director table in sql
    '''
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()

    drop_movies = '''
        DROP TABLE IF EXISTS "Movies";
    '''

    create_movies = '''
        CREATE TABLE IF NOT EXISTS "Movies" (
            "Id"            INTEGER PRIMARY KEY AUTOINCREMENT,
            "MovieTitle"    TEXT NOT NULL,
            "Rank"          INTEGER,
            "Category"      TEXT NOT NULL,
            "Length"        INTEGER NOT NULL,
            "Genre"         TEXT,
            "ReleaseDate"   TEXT NOT NULL,
            "ReleaseCountry" TEXT NOT NULL,
            "Rating"        REAL NOT NULL,
            "DirectorId"    INTEGER NOT NULL,
            "Image"         TEXT,
            FOREIGN KEY ("DirectorId") REFERENCES Directors("Id")
        );
    '''

    drop_directors = '''
        DROP TABLE IF EXISTS "Directors";
    '''

    create_directors = '''
        CREATE TABLE IF NOT EXISTS "Directors" (
            "Id"            INTEGER PRIMARY KEY AUTOINCREMENT,
            "FirstName"     TEXT NOT NULL,
            "LastName"      TEXT NOT NULL,
            "Link"          TEXT
        );
    '''

    cur.execute(drop_directors)
    cur.execute(create_directors)
    cur.execute(drop_movies)
    cur.execute(create_movies)

    conn.commit()
    conn.close()


def insert_movies(movies, url2fk):
    ''' insert row in Movie table

    Parameters
    ----------
    movies: list
        a list of movies

    url2fk: dictionary
        transform url of director page to foreign key id in Movie table
    '''
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()

    insert_command = '''
        INSERT INTO Movies
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    for movie in movies:
        directorId = url2fk[list(movie.director.values())[0]]
        values = [movie.name, movie.rank, " ".join(movie.category), movie.length, movie.genre, movie.release_date, movie.release_country, movie.rating, directorId, movie.image]
        cur.execute(insert_command, values)

    conn.commit()
    conn.close()


def insert_directors(directors):
    '''insert row in Director table
    '''
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()

    insert_command = '''
        INSERT INTO Directors
        VALUES (NULL, ?, ?, ?)
    '''

    url2id = {}
    for i, director in enumerate(directors):
        url2id[director[1]] = i+1              # director's name is not unique, thus using url as the index key
        values = [director[0].split(' ')[0], director[0].split(' ')[-1], director[1]]
        # insert_raw_into_table(cur, table_name=Directors, values=values)
        cur.execute(insert_command, values)

    conn.commit()
    conn.close()

    return url2id


def get_top_k_movies_command(top_k):
    command = '''
    SELECT MovieTitle, Rank, Category, Length, Genre, ReleaseDate, ReleaseCountry, Rating, FirstName||' '||LastName, Image
    FROM Movies
        JOIN Directors
            ON Movies.DirectorId = Directors.Id
    ORDER BY Rank
    LIMIT {}
    '''.format(top_k)

    return command

def get_top_k_movies(top_k):
    command = get_top_k_movies_command(top_k)
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()
    cur.execute(command)
    results = list(cur.fetchall())
    conn.close()

    return results

def get_distribution_of_release_date(top_k):
    distribution = {}
    left = top_k

    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()

    for year in range(1960, 2020, 10):
        command = '''
        SELECT COUNT(*)
        FROM 
            (SELECT *
            FROM Movies
            ORDER BY Rank
            LIMIT {num})
        WHERE ReleaseDate BETWEEN \'{date_1}\' AND \'{date_2}\'
        '''.format(num=top_k, date_1 = str(year) + '-01-01', date_2 = str(year + 9) + '-12-31')
        cur.execute(command)
        distribution[str(year)+'s'] = cur.fetchall()[0][0]
        left -= distribution[str(year)+'s']
    distribution['else'] = left
    conn.close()

    return distribution

def get_most_popular_director(top_k):
    command = '''
    SELECT FullName, COUNT(*), Link
    FROM
        (SELECT MovieTitle, Rank, Category, Length, Genre, ReleaseDate, ReleaseCountry, Rating, Image, FirstName||' '||LastName AS FullName, Link
        FROM Movies
            JOIN Directors
                ON Movies.DirectorId = Directors.Id
        ORDER BY Rank
        LIMIT {num})
    GROUP BY FullName
    ORDER BY COUNT(*) DESC
    '''.format(num = top_k)

    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()
    cur.execute(command)
    results = list(cur.fetchall())
    conn.close()

    return results

def release_date_plot(date_distribution):
    xvals = list(date_distribution.keys())
    yvals = list(date_distribution.values())

    bar_data = go.Bar(x=xvals, y=yvals)
    basic_layout = go.Layout()
    fig = go.Figure(data = bar_data, layout = basic_layout)

    fig.show()



#############################################################
# flask part ################################################
#############################################################
app = Flask(__name__)

@app.route('/')
def homepage():
    return render_template('home.html')

@app.route('/top_movies/<top_k>', methods=['POST', 'GET'])
def top_movies_render(top_k):
    '''render the top k movies in the chrome
    '''
    if request.method == 'POST':
        top_k = request.form['top_k']
    top_k_movies = get_top_k_movies(int(top_k))
    tkm = [(m[0], m[1]) for m in top_k_movies]
    return render_template('movie_list.html', movies=tkm)

@app.route('/movies/<no>')
def movie_detail_render(no):
    '''render the chosen movie detail page
    '''
    movies = get_top_k_movies(250)
    movie = movies[int(no)-1]
    return render_template('movie_detail.html',
                           movietitle=movie[0], rank=movie[1],
                           category=movie[2], length=movie[3],
                           genre=movie[4],release_date=movie[5],
                           release_country=movie[6],rating=movie[7],
                           director=movie[8], img=movie[9])

@app.route('/popular_director/<top_k>')
def popular_director(top_k):
    '''render popular directors in the page
    '''
    directors = get_most_popular_director(top_k)
    return render_template('director_list.html', directors=directors, k=top_k)

@app.route('/<nm>/knownfor/<url>')
def director_knownfor_render(nm, url):
    '''render the page of diretor and his/her famous movies
    '''
    poster, knownfor = get_director_knownfor(url.replace('_', '/'))

    return render_template('director_detail.html', name=nm.replace('-', ' '), poster=poster, movies=knownfor)

@app.route('/distribution_of_release_date/<top_k>')
def distribution_of_release_date(top_k):
    '''plot the bar plot of the distribution of release date in flask
    '''
    date_distribution = get_distribution_of_release_date(int(top_k))

    xvals = list(date_distribution.keys())
    yvals = list(date_distribution.values())

    bar_data = go.Bar(x=xvals, y=yvals, width=0.6)
    basic_layout = go.Layout(
                            xaxis = go.XAxis(domain = [0,0.6]))
    fig = go.Figure(data = bar_data, layout = basic_layout)

    div = fig.to_html(full_html=False)
    return render_template("plot.html", plot_div=div, top_k=top_k)


if __name__ == '__main__':

    if not os.path.exists(DATABASE_FILE):
        ###############################################
        # Part 1: if database doesn't exist, scrapping and
        # crawling data from the web
        #
        # Warning: this procedure is really time consuming even with the cache.
        # If you just want to test part 1 and 2, small k is recommanded. Otherwise, please run
        # this program with database.
        ###############################################
        dic = build_movie_url_dict("/chart/top")
        while True:
            k = input("Enter a number of records you want to get(max:250):")
            if k.isnumeric():
                k = int(k)
                if k > 250:
                    print("Out of boundary. Please enter again.")
                    continue
                break
            else:
                print("Invalid input. Please enter again.")
                continue
        movies_top_250 = get_top_ranked_movies(dic, k)
        directors = get_directors_from_movies(movies_top_250)

        ###############################################
        # Part 2: create database from scrapped data
        ###############################################
        create_sql_tables()
        url2fk = insert_directors(directors)
        insert_movies(movies_top_250, url2fk)

    ##################################################
    # Part 3: Showing information of the data by Flask app
    ##################################################

    print("run app")
    app.run(debug=True)




# Questions (6 total)

For each of the questions below, answer as if you were in an interview, explaining and justifying your answer with two to three paragraphs as you see fit. For coding answers, explain the relevant choices you made writing the code.

## Question 1 
- What is the most influential book or blog post you’ve read regarding web development?

A: I really enjoyed an online book `Explore flask` - It outlines how to use flask to build simple websites, touches on best practices in organizing the code base, as well as tests.

## Question 2 
- Tell me about a web application you have built. Why did you choose to build it? What did you learn? What challenges did you face and how did you overcome them?

A: I bulid a catalog application for udacity full stack web developer nano degree. The project was aimed at building an end-to-end web app, it includes data model, RESTful APIs that serve JSON and XML output, and front end HTML/CSS/JS that renders the items and categories in a catalog. 

Through building the app I have learned how routing works, how to design data model to represent relevant data, separting the business layer with data layer, how session works, how to prevent xsrf, and how to implement authorization and authentication with G+ and facebook login. 

The challenges for me lie in organizing the code base, and understanding how session works. For this project I started from a blank canvas, most of my backend code lived in a single `application.py` file and a `db.py` file. As the project went along, the code got longer and hard to navigate. With the help of udacity tutors I read the online book `Explore flask` and found blueprints to organize project structure. And by searching on the concept of session, and examples of G+ login, I understood xsrf is prevented by assigning a random token, and matching the returned request to the token. I realized that looking very closely at the example code and understanding the intention is a good way to get past blocks.


## Question 3 
- Write a function that takes a list of strings and returns a single string that is an HTML unordered list (<ul>...</ul>) of those strings. You should include a brief explanation of your code. Then, what would you have to consider if the original list was provided by user input?

```python
def my_ul(lst):
    """return unordered list in html of input string list"""
    lis = '\n'.join(['<li>%s</li>' %string for string in lst])
    return '<ul>%s</ul>' %lis
```

The code wraps each string in the list with `li` tag, join them together, and wrap the joined string with a `ul` tag, to make HTML unordered list. 

If the original list is provided by the user, we would need to escape user input, in order to prevent the user from injecting arbitrary characters such as html tags, that break the page. We should use existing escape methods instead of implementing our own, to properly consider all edge cases.


## Question 4 
- List 2-3 attacks that web applications are vulnerable to. How do these attacks work? How can we prevent those attacks?

A: Here are three:
- User input can include random html tags that expose information like user password. We can prevent by properly escape user input, i.e. opening tag `<` is saved as `&lt;`, and converted back when rendering html. 

- SQL injection: user input that get saved into the database can include malicious statements like `;drop table xxx`. Instead of using concatenated string using raw user input in DB queries, proper escaping is used to prevent SQL injection.

- XSRF (cross site request forgery): Another site can send a request pretending to be an authorized user, and get private user information or perform actions on user accounts. We can prevent XSRF by using security token with each request saved in session, and confirming the request returns back the same token. 


## Question 5 
- Here is some starter code for a Flask Web Application. Expand on that and include a route that simulates rolling two dice and returns the result in JSON. You should include a brief explanation of your code.

```python
from flask import Flask, jsonify
app = Flask(__name__)

import json
import random

@app.route('/2dice.json')
def roll_dice():
    """return json result of two dice rolls"""
    dice = [random.choice(range(1, 7)), random.choice(range(1, 7))]
    return jsonify(dice=dice)


@app.route('/')
def hello_world():
    return 'Hello World!'

if __name__ == '__main__':
    app.debug = True
    app.run()
```

Route `/2dice.json` returns the result of rolling two dice in json format, in a list of two rolled results, i.e. integers between 1 and 6.


## Question 6
Before answering the final question, insert a job description for a full-stack developer position of your choice!

Your answer for Question 6 should be targeted to the company/job-description you chose.

Question 6 - If you were to start your full-stack developer position today, what would be your goals a year from now?

### Job description - [Uber](https://careers-uber.icims.com/jobs/12396/software-engineer---full-stack/job?mobile=false&width=878&height=500&bga=true&needsRedirect=false&jan1offset=-480&jun1offset=-420)

- Fast learner. We’re looking for software engineers who thrive on learning new technologies and don’t believe in one-size-fits-all solutions. You should be able to adapt easily to meet the needs of our massive growth and rapidly evolving business environment. You have advanced knowledge of at least one scripting language (e.g. Python or JavaScript) and knowledge of or eagerness to learn: MySQL, PostgreSQL, Redis, Kafka, and ElasticSearch.

- Fearlessness. You think a working proof-of-concept is the best way to make a point. You strive on proving that speed and quality are not conflicting; that you can achieve both at the same time.

- Versatility. In addition to having an intimate knowledge of the whole web stack, you understand how all the pieces fit together (front-end, database, network layer, etc.) and how they impact the performance of your application.

- Strong architecture chops. You know how to build highly scalable, robust, and fault-tolerant services that support our unique rate-of-growth requirements. You stay up-to-date with the latest architectural trends.

- Passion. You feel ownership over everything you ship; you'd never call code "released" until you’re confident it’s correct. You pride yourself on efficient monitoring, strong documentation, and proper test coverage.

- A team player. You believe that you can achieve more on a team — that the whole is greater than the sum of its parts. You rely on others' candid feedback for continuous improvement.

- Design and business acumen. You understand requirements beyond the written word. Whether you’re working on an API used by other developers, an internal tool consumed by our operation teams, or a feature used by millions of riders, your attention to details leads to a delightful user experience.


### Answer
A year from now, I would like to 
- become well versed in a few languages such as Python, JavaScript, 
- well versed in datastores, be it relational DB or noSQL DB, 
- properly use cache to improve site performance, 
- Familiar with a framework such as flask, django
- Familiar with a front end framework such as AngularJS
- be able to implement designer's wireframe with HTML/CSS/JS
- be able to design and build a feature end-to-end
- Write unittests as well as integration tests to properly vet the features I build
- Perform online experimentation to access business impact of the new featuers

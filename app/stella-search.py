from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import os
import requests
import json
import random
import ast
import datetime

# STELLA_APP_API = 'http://0.0.0.0:8000/stella/api/v1/'
# JL_PATH = '../data/index'
STELLA_APP_API = 'http://app:8000/stella/api/v1/'
JL_PATH = '../data/index'


def index_data(jl_path):
    corpus = {}
    with open(jl_path) as jl:
        for line in jl:
            j = json.loads(line)
            corpus[j['id']] = json.loads(line)

    return corpus


def doc_list(id_list):
    return [corpus.get(id) for id in id_list]


def single_doc(id):
    doc = corpus.get(id)
    # random_ids = random.choices(list(corpus.keys()), k=4)
    req = requests.get(STELLA_APP_API + "recommendation/publications?itemid=" + id).json()
    recommendations = doc_list([v['docid'] for k, v in req.get('body').items()])

    # send feedback for recommendation of publications
    click_dict = req.get('body')
    rec_id = req.get('header').get('rid')
    if len(click_dict) > 0:
        session_start_date = datetime.datetime.now()
        session_end_date = session_start_date + datetime.timedelta(0, random.randint(10, 3000))
        rand_int = random.randint(1, len(click_dict))
        random_clicks = random.sample(range(1, len(click_dict)), random.randint(1, 3))
        random.sample(range(1, 10), random.randint(1, 9))
        for key, val in click_dict.items():
            if int(key) in random_clicks:
                click_dict.update({key: {'docid': req.get('body').get(key).get('docid'),
                                         'system': req.get('body').get(key).get('type'),
                                         'clicked': True,
                                         'date': session_start_date.strftime("%Y-%m-%d %H:%M:%S")}})
            else:
                click_dict.update({key: {'docid': req.get('body').get(key).get('docid'),
                                         'system': req.get('body').get(key).get('type'),
                                         'clicked': False,
                                         'date': None}})

        # have to use json.dumps(click_dict) since requests cannot send dict in dict as payload
        # see also this thread: https://stackoverflow.com/questions/38380086/sending-list-of-dicts-as-value-of-dict-with-requests-post-going-wrong
        # the stella-server will accept string-formatted json as well as conventional json
        payload = {
            'start': session_start_date.strftime("%Y-%m-%d %H:%M:%S"),
            'end': session_end_date.strftime("%Y-%m-%d %H:%M:%S"),
            'interleave': True,
            'clicks': json.dumps(click_dict)
            # 'clicks': click_dict
        }
        req = requests.post(STELLA_APP_API + "recommendation/" + str(rec_id) + "/feedback", data=payload)

    # return recommendations
    return {'title': doc['title'],
            'type': doc['type'],
            'id': id,
            'source': doc['publisher'],
            # 'abstract': (doc['abstract'][0] if type(doc['abstract']) is list else doc['abstract'])[:500] + '...',
            'abstract': (doc['abstract'][0] if type(doc['abstract']) is list else doc['abstract'])[:1200] + '...',
            'similar_items': recommendations[:3]}


class SearchForm(FlaskForm):
    query = StringField('', validators=[DataRequired()])
    submit = SubmitField('Search')


app = Flask(__name__)
app.config['SECRET_KEY'] = 'udonotknow'
bootstrap = Bootstrap()
bootstrap.init_app(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    form = SearchForm()
    if form.validate_on_submit():
        query = form.query.data
        form.query.data = query
        req = requests.get(STELLA_APP_API + "ranking?query=" + query).json()
        result_list = req.get('body').values()
        id_list = [doc['docid'] for doc in result_list]
        results = doc_list(id_list)

        # send feedback directly after the ranking is retrieved
        session_id = req.get('header').get('sid')
        ranking_id = req.get('header').get('rid')

        click_dict = req.get('body')
        if len(click_dict) > 0:
            session_start_date = datetime.datetime.now()
            session_end_date = session_start_date + datetime.timedelta(0, random.randint(10, 3000))
            rand_int = random.randint(1, len(click_dict))
            random_clicks = random.sample(range(1, len(click_dict)), random.randint(1, 3))
            random.sample(range(1, 10), random.randint(1, 9))
            for key, val in click_dict.items():
                if int(key) in random_clicks:
                    click_dict.update({key: {'docid': req.get('body').get(key).get('docid'),
                                             'system': req.get('body').get(key).get('type'),
                                             'clicked': True,
                                             'date': session_start_date.strftime("%Y-%m-%d %H:%M:%S")}})
                else:
                    click_dict.update({key: {'docid': req.get('body').get(key).get('docid'),
                                             'system': req.get('body').get(key).get('type'),
                                             'clicked': False,
                                             'date': None}})

            # have to use json.dumps(click_dict) since requests cannot send dict in dict as payload
            # see also this thread: https://stackoverflow.com/questions/38380086/sending-list-of-dicts-as-value-of-dict-with-requests-post-going-wrong
            # the stella-server will accept string-formatted json as well as conventional json
            payload = {
                'start': session_start_date.strftime("%Y-%m-%d %H:%M:%S"),
                'end': session_end_date.strftime("%Y-%m-%d %H:%M:%S"),
                'interleave': True,
                'clicks': json.dumps(click_dict)
                # 'clicks': click_dict
            }

            r = requests.post(STELLA_APP_API + 'ranking/' + str(ranking_id) + '/feedback', data=payload)
            # r_json = json.loads(r.text)
            # print(r_json, ranking_id)

    return render_template('index.html', form=form, results=results)


def item_details(id):
    return {"title": "title goes here",
            "id": id,
            "date": "date goes here",
            "publisher": "publisher goes here",
            "type": "type goes here"}


@app.route('/detail/<string:docid>', methods=['GET'])
def detail(docid):
    l = []
    doc = single_doc(docid)
    try:

        results = requests.get(STELLA_APP_API + "recommendation/datasets?itemid=" + docid).json()

        # send feedback for recommendation of publications
        click_dict = results.get('body')
        rec_id = results.get('header').get('rid')
        if len(click_dict) > 0:
            session_start_date = datetime.datetime.now()
            session_end_date = session_start_date + datetime.timedelta(0, random.randint(10, 3000))
            rand_int = random.randint(1, len(click_dict))
            random_clicks = random.sample(range(1, len(click_dict)), random.randint(1, 3))
            random.sample(range(1, 10), random.randint(1, 9))
            for key, val in click_dict.items():
                if int(key) in random_clicks:
                    click_dict.update({key: {'docid': results.get('body').get(key).get('docid'),
                                             'system': results.get('body').get(key).get('type'),
                                             'clicked': True,
                                             'date': session_start_date.strftime("%Y-%m-%d %H:%M:%S")}})
                else:
                    click_dict.update({key: {'docid': results.get('body').get(key).get('docid'),
                                             'system': results.get('body').get(key).get('type'),
                                             'clicked': False,
                                             'date': None}})

            # have to use json.dumps(click_dict) since requests cannot send dict in dict as payload
            # see also this thread: https://stackoverflow.com/questions/38380086/sending-list-of-dicts-as-value-of-dict-with-requests-post-going-wrong
            # the stella-server will accept string-formatted json as well as conventional json
            payload = {
                'start': session_start_date.strftime("%Y-%m-%d %H:%M:%S"),
                'end': session_end_date.strftime("%Y-%m-%d %H:%M:%S"),
                'interleave': True,
                'clicks': json.dumps(click_dict)
                # 'clicks': click_dict
            }
            req = requests.post(STELLA_APP_API + "recommendation/" + str(rec_id) + "/feedback", data=payload)

        for k, v in results.get('body').items():
            id = v.get('doc_id')
            detail = item_details(id)

            if "publisher" not in detail:
                l.append({"Title": detail["title"],
                          "Id": detail["id"],
                          "Date": detail["date"],
                          "Publisher": "Unidentified",
                          "Type": detail["type"]})
            else:
                l.append({"Title": detail["title"],
                          "Id": detail["id"],
                          "Date": detail["date"],
                          "Publisher": detail["publisher"],
                          "Type": detail["type"]})
    except Exception as e:
        # raise e
        pass

    return render_template('detail.html', result=doc, similar_items=l[:3], query=docid)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    for file in os.listdir(JL_PATH):
        if file.endswith(".jsonl"):
            corpus = index_data(os.path.join(JL_PATH, file))
    if port == 5000:
        app.debug = True

    app.run(host='0.0.0.0', port=port)

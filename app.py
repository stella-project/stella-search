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

JL_PATH = './data/index'


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
    req = requests.get("http://0.0.0.0:8080/stella/api/v1/recommendation/publications?item_id=" + id).json()
    recommendations = doc_list([v['docid'] for k, v in req.items()])

    return {'title': doc['title'],
            'type': doc['type'],
            'id': id,
            'source': doc['publisher'],
            'abstract': doc['abstract'],
            'similar_items': recommendations}


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
        req = requests.get("http://0.0.0.0:8080/stella/api/v1/ranking?query=" + query).json()
        result_list = req.values()
        id_list = [doc['docid'] for doc in result_list]
        results = doc_list(id_list)

    return render_template('index.html', form=form, results=results)


def item_details(id):
    return {"title": "title goes here",
            "id": id,
            "date": "date goes here",
            "publisher": "publisher goes here",
            "type": "type goes here"}


@app.route('/detail/<string:doc_id>', methods=['GET'])
def detail(doc_id):
    l = []
    doc = single_doc(doc_id)
    try:
        results = requests.get("http://0.0.0.0:8080/stella/api/v1/recommendation/datasets?item_id=" + doc_id).json()

        for k, v in results.items():
            id = v.get('docid')
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
        raise e

    return render_template('detail.html', result=doc, similar_items=l, query=doc_id)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    for file in os.listdir(JL_PATH):
        if file.endswith(".jsonl"):
            corpus = index_data(os.path.join(JL_PATH, file))
    if port == 5000:
        app.debug = True

    app.run(host='0.0.0.0', port=port)

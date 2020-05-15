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

SITE = 'GESIS'  # 'GESIS' or 'LIVIVO'
JL_PATH = './data/livivo/pubmed_2015_2016.jsonl'
GESIS_DATA_PUB = './data/lini_dic_100_samp_Publication-ALL.json'


def index_data(jl_path):
    corpus = {}
    if SITE == 'LIVIVO':
        with open(jl_path) as jl:
            for line in jl:
                j = json.loads(line)
                corpus[j['DBRECORDID']] = json.loads(line)

    if SITE == 'GESIS':
        with open(jl_path) as jl:
            for line in jl:
                j = ast.literal_eval(line)
                # j = json.loads(line.replace("\'", "\""))
                corpus[j['id']] = j

    return corpus


def doc_list(id_list):
    dl = []
    if SITE == 'LIVIVO':
        for id in id_list:
            doc = corpus.get(id)
            dl.append({'title': doc['TITLE'][0],
                       'type': doc['DBDOCTYPE'][0],
                       'id': id,
                       'source': doc['SOURCE'][0]})
    if SITE == 'GESIS':
        for id in id_list:
            doc = corpus.get(id)
            dl.append({'title': doc['title'],
                       'type': doc['type'],
                       'id': id,
                       'source': doc['data_source']})

    return dl


def single_doc(id):
    doc = corpus.get(id)
    random_ids = random.choices(list(corpus.keys()), k=4)
    recommendations = doc_list(random_ids)

    if SITE == 'LIVIVO':
        return {'title': doc['TITLE'][0],
                'type': doc['DBDOCTYPE'][0],
                'id': id,
                'source': doc['SOURCE'][0],
                'abstract': (doc.get('ABSTRACT')[0] if doc.get('ABSTRACT') is not None else 'no abstract'),
                'similar_items': recommendations}

    if SITE == 'GESIS':
        return {'title': doc['title'],
                'type': doc['type'],
                'id': id,
                'source': doc['data_source'],
                'abstract': (doc.get('abstract') if doc.get('abstract') is not None else 'no abstract'),
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

        # results = list(req.values())

        result_list = req.values()
        id_list = [doc['docid'] for doc in result_list]

        results = doc_list(id_list)

    if SITE == 'LIVIVO':
        return render_template('index_pubmed.html', form=form, results=results)
    if SITE == 'GESIS':
        return render_template('index.html', form=form, results=results)


def item_details(id):
    id_req = requests.get("http://193.175.238.15:5555/api/items/" + id).json()
    return(id_req)


@app.route('/detail/<string:doc_id>', methods=['GET'])
def detail(doc_id):
    # results = requests.get(" http://0.0.0.0/stella/api/v1/recommend_dataset/" + doc_id).json()
    # l = {}
    # for i in range(len(results['similar_items'])):
    #     key = results['similar_items'][i]["id"]
    #     detail = item_details(key)
    #     if detail["type"] == "research_data" :
    #         if "publisher" not in detail:
    #             l[key] = {"Title": detail["title"], "Id": detail["id"], "Date": detail["date"],"Publisher": "Unidentified", "Type": detail["type"] }
    #         else :
    #             l[key] = {"Title": detail["title"], "Id": detail["id"], "Date": detail["date"],"Publisher": detail["publisher"], "Type": detail["type"] }
    #
    # return render_template('detail.html', results=results, id_results = l , query = doc_id)
    doc = single_doc(doc_id)
    return render_template('detail_pubmed.html', result=doc)


@app.route('/detail_pubmed/<string:doc_id>', methods=['GET'])
def detail_pubmed(doc_id):
    doc = single_doc(doc_id)
    return render_template('detail_pubmed.html', result=doc)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # corpus = index_data(JL_PATH)
    corpus = index_data(GESIS_DATA_PUB)
    if port == 5000:
        app.debug = True

    app.run(host='0.0.0.0', port=port)

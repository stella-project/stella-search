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
import logging

logging.basicConfig(level=logging.DEBUG)

STELLA_APP_API = os.environ.get("STELLA_APP_ADDRESS", "http://stella-app:8000") + "/stella/api/v1/"
PUB_PATH = os.environ.get("PUB_PATH", "../data/index/publication.jsonl")
DATA_PATH = os.environ.get("DATA_PATH", "../data/index/dataset.jsonl")

ranking_list = []
publication_list = []
dataset_list = []
ranking_id = None
pub_rec_id = None
data_rec_id = None
rid = None

def index_data(jl_path):
    corpus = {}
    with open(jl_path) as jl:
        for line in jl:
            j = json.loads(line)
            corpus[j["id"]] = json.loads(line)
    logging.info("Indexed %s documents from %s", len(corpus), jl_path)
    return corpus


def doc_list(id_list, type):
    if type == 'publication':
        return [publication_corpus.get(id) for id in id_list]
    elif type == 'dataset':
        return [dataset_corpus.get(id) for id in id_list]

def send_feedback(result_type):
    global ranking_list, publication_list, dataset_list, ranking_id, pub_rec_id, data_rec_id, rid

    if result_type == 'RANK':
        if rid == ranking_id:
            return
        result_list = ranking_list
        rid = ranking_id
    elif result_type == 'REC_PUB':
        if rid == pub_rec_id:
            return
        result_list = publication_list
        rid = pub_rec_id
    else:
        if rid == data_rec_id:
            return
        result_list = dataset_list
        rid = data_rec_id

    

    click_dict = {}
    for i, d in enumerate(result_list):
        click_dict[str(i)] = d
    
    if len(click_dict) > 0:
        session_start_date = datetime.datetime.now()
        session_end_date = session_start_date + datetime.timedelta(
            0, random.randint(10, 3000)
        )
        random_clicks = random.sample(range(1, len(click_dict)), random.randint(1, 3))
        for key, val in click_dict.items():
            if int(key) in random_clicks:
                click_dict.update({key: {'docid': result_list[int(key)].get('docid'),
                                             'type': result_list[int(key)].get('type'),
                                             'clicked': True,
                                             'date': session_start_date.strftime("%Y-%m-%d %H:%M:%S")}})
            else:
                click_dict.update({key: {'docid': result_list[int(key)].get('docid'),
                                             'type': result_list[int(key)].get('type'),
                                             'clicked': False,
                                             }})

        
        payload = {
            "start": session_start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "end": session_end_date.strftime("%Y-%m-%d %H:%M:%S"),
            "interleave": True,
            "clicks": json.dumps(click_dict),
            # 'clicks': click_dict
        }

        if result_type == 'RANK':
            feedback_req = requests.post(
                STELLA_APP_API + "ranking/" + str(rid) + "/feedback", data=payload,
            )
        else:
            feedback_req = requests.post(
                STELLA_APP_API + "recommendation/" + str(rid) + "/feedback", data=payload
            )

        feedback_req_json = json.loads(feedback_req.text)
        logging.info(f">>>>>>>>> FEEDBACK RESPONSE ({rid}):  {feedback_req_json}")


class SearchForm(FlaskForm):
    query = StringField("", validators=[DataRequired()])
    submit = SubmitField("Search")


app = Flask(__name__)
app.config["SECRET_KEY"] = "udonotknow"
bootstrap = Bootstrap()
bootstrap.init_app(app)


@app.route("/", methods=["GET", "POST"])
def index():
    global ranking_list, ranking_id
    results = []
    form = SearchForm()

    try:
        if form.validate_on_submit():
            query = form.query.data
            form.query.data = query
            req = requests.get(STELLA_APP_API + "ranking?query=" + query).json()

            ranking_list = req.get("body")

            id_list = [doc["docid"] for doc in ranking_list]

            results = doc_list(id_list, 'publication')

            logging.info(
                ">>>>>>>>> Retrieved %s results for query: %s", len(results), query
            )

            # send feedback directly after the ranking is retrieved
            #session_id = req.get("header").get("sid")
            ranking_id = req.get("header").get("rid")

    except Exception as e:
        logging.error(">>>>>>>>> ERROR %s", e)

    return render_template("index.html", form=form, results=results)


def item_details(id):
    return {
        "title": "title goes here",
        "id": id,
        "date": "date goes here",
        "publisher": "publisher goes here",
        "type": "type goes here",
    }



def get_publication_recommendations(docid):
    global publication_list, pub_rec_id
    try:
        doc = publication_corpus.get(docid)
        req = requests.get(
            STELLA_APP_API + "recommendation/publications?itemid=" + docid
        ).json()
        pub_ids = doc_list([v["docid"] for k, v in req.get("body").items()], 'publication')

        publication_list = list(req.get("body").values())
        pub_rec_id = req.get("header").get("rid")


        abstract = None
        if doc['abstract'] is not None:
            if type(doc['abstract']) is list:
                abstract = doc['abstract'][0]
            else:
                abstract = doc['abstract']
        if abstract is not None:
            abstract = abstract[:1200] + '...'
        else:
            abstract = 'nix hier'

        return {'title': doc['title'],
                'type': 'publication', #doc['type'],
                'id': docid,
                'source': 'Unidentified', #doc['publisher'],
                # 'abstract': (doc['abstract'][0] if type(doc['abstract']) is list else doc['abstract'])[:500] + '...',
                'abstract': abstract,
                'similar_items': pub_ids[:3]}
    except Exception as e:
        logging.error(">>>>>>>>> ERROR %s", e)

        return {'title': '',
                'type': '', #doc['type'],
                'id': docid,
                'source': 'Unidentified', #doc['publisher'],
                # 'abstract': (doc['abstract'][0] if type(doc['abstract']) is list else doc['abstract'])[:500] + '...',
                'abstract': '',
                'similar_items': []}


def get_dataset_recommendations(docid):
    global dataset_list, data_rec_id
    rec_list = []
    try:

        req = requests.get(
            STELLA_APP_API + "recommendation/datasets?itemid=" + docid
        ).json()


        data_ids = doc_list([v["docid"] for k, v in req.get("body").items()], 'dataset')
        for i, d in enumerate(data_ids):
            if type(d['title']) == list:
                data_ids[i]['title'] = d['title'][0]
            if type(d['doi']) == list:
                data_ids[i]['doi'] = d['doi'][0]

        data_rec_id = req.get("header").get("rid")

        rec_list = data_ids
        
        '''
        for k, v in req.get("body").items():
            id = v.get("docid")
            detail = item_details(id)

            rec_list.append(
                    {
                        "Title": detail["title"],
                        "Id": detail["id"],
                        "Date": detail["date"],
                        "Publisher": detail.get('publisher', 'Unidentified'),
                        "Type": detail["type"],
                    }
            )
        '''
    except Exception as e:
        logging.error(">>>>>>>>> ERROR %s", e)
        # raise e
        pass

    dataset_list = rec_list
    return rec_list

    


@app.route("/detail/<string:docid>/<string:result_type>", methods=["GET"])
def detail(docid, result_type):
    send_feedback(result_type)

    publications_rec = get_publication_recommendations(docid)
    datasets_rec = get_dataset_recommendations(docid)

    return render_template("detail.html", publications=publications_rec, datasets=datasets_rec[:3], query=docid)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    publication_corpus = {}
    dataset_corpus = {}
    if os.path.exists(PUB_PATH):
        publication_corpus = index_data(PUB_PATH)

    if os.path.exists(DATA_PATH):
        dataset_corpus = index_data(DATA_PATH)
    if port == 5000:
        app.debug = True

    app.run(host="0.0.0.0", port=port)

import ast
import datetime
import json
import logging
import os
import random

import requests
from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)s in %(module)s (%(lineno)d): %(message)s",
)

STELLA_APP_API = (
    os.environ.get("STELLA_APP_ADDRESS", "http://stella-app:8000") + "/stella/api/v1/"
)
PUB_PATH = os.environ.get("PUB_PATH", "../data/index/publication.jsonl")
DATA_PATH = os.environ.get("DATA_PATH", "../data/index/dataset.jsonl")

ranking_list = []
recommendation_list = []
ranking_id = None
recommendation_id = None
rid = None
recid = None


def index_data(jl_path):
    corpus = {}
    with open(jl_path) as jl:
        for line in jl:
            j = json.loads(line)
            corpus[j["id"]] = json.loads(line)
    logging.info("Indexed %s documents from %s", len(corpus), jl_path)
    return corpus


def doc_list(id_list):
    return [publication_corpus.get(id) for id in id_list]


def send_feedback(result_type):
    global ranking_list, recommendation_list, ranking_id, recommendation_id, rid, recid

    if result_type == "RANK":
        if rid == ranking_id:
            return
        result_list = ranking_list
        rid = ranking_id
    else:
        if rid == recommendation_id:
            return
        result_list = recommendation_list
        rid = recid

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
            click_dict[key] = {
                "docid": val.get("docid"),
                "type": val.get("type"),
                "clicked": False,
            }
            if int(key) in random_clicks:
                click_dict[key].update(
                    {
                        "clicked": True,
                        "date": session_start_date.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

        payload = {
            "start": session_start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "end": session_end_date.strftime("%Y-%m-%d %H:%M:%S"),
            "interleave": True,
            "clicks": json.dumps(click_dict),
        }

        if result_type == "RANK":
            feedback_req = requests.post(
                STELLA_APP_API + "ranking/" + str(rid) + "/feedback",
                data=payload,
            )
        else:
            feedback_req = requests.post(
                STELLA_APP_API + "recommendation/" + str(rid) + "/feedback",
                data=payload,
            )
        if feedback_req.status_code != 200:
            logging.error(
                "Feedback request failed with status code %s: %s",
                feedback_req.status_code,
                feedback_req.text,
            )
            return

        feedback_req_json = json.loads(feedback_req.text)
        logging.info(f"FEEDBACK RESPONSE ({rid}):  {feedback_req_json}")


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
            if not req.get("header"):
                logging.error("Could not retrieve ranking for query: %s", query)
                return render_template("index.html", form=form, results=results)
            else:
                logging.info(req)

            ranking_list = req.get("body").values()

            id_list = [doc["docid"] for doc in ranking_list]

            results = doc_list(id_list)

            logging.info("Retrieved %s results for query: %s", len(results), query)

            # send feedback directly after the ranking is retrieved
            # session_id = req.get("header").get("sid")
            ranking_id = req.get("header").get("rid")

    except Exception as e:
        logging.error("ERROR %s", e)

    return render_template("index.html", form=form, results=results)


def item_details(id):
    return {
        "title": "title goes here",
        "id": id,
        "date": "date goes here",
        "publisher": "publisher goes here",
        "type": "type goes here",
    }


def get_recommendations(docid):
    global publication_list, pub_rec_id

    doc = publication_corpus.get(docid)
    req = requests.get(STELLA_APP_API + "recommendation?itemid=" + docid)

    req = req.json()
    logging.info(req)

    pub_ids = doc_list([v["docid"] for k, v in req.get("body").items()])

    publication_list = list(req.get("body").values())
    pub_rec_id = req.get("header").get("rid")

    abstract = None
    if doc["abstract"] is not None:
        if type(doc["abstract"]) is list:
            abstract = doc["abstract"][0]
        else:
            abstract = doc["abstract"]
    if abstract is not None:
        abstract = abstract[:1200] + "..."
    else:
        abstract = "nix hier"

    return {
        "title": doc["title"],
        "type": "publication",  # doc['type'],
        "id": docid,
        "source": "Unidentified",  # doc['publisher'],
        # 'abstract': (doc['abstract'][0] if type(doc['abstract']) is list else doc['abstract'])[:500] + '...',
        "abstract": abstract,
        "similar_items": pub_ids[:3],
    }


@app.route("/detail/<string:docid>/<string:result_type>", methods=["GET"])
def detail(docid, result_type):
    send_feedback(result_type)

    document = publication_corpus.get(docid)
    recommendations = get_recommendations(docid)

    return render_template(
        "detail.html",
        document=document,
        recommendations=recommendations,
        query=docid,
    )


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

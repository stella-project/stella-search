import ast
import datetime
import json
import logging
import os
import time

import requests
from flask import Flask, render_template, session
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

DATE_FMT = "%Y-%m-%d %H:%M:%S"

# A STELLA session (sid) ends after this many seconds without user activity.
SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", 5 * 60))

# State of the most recently shown result lists (single-user demo, module-level).
# Each entry holds the list returned by the STELLA app, its result id (rid),
# the time it was shown, and the clicks recorded on it so far (docid -> click date).
result_lists = {
    "RANK": {"items": [], "rid": None, "start": None, "clicks": {}},
    "REC_PUB": {"items": [], "rid": None, "start": None, "clicks": {}},
}


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


def set_result_list(result_type, items, rid):
    """Remember a newly shown result list and reset its recorded clicks."""
    result_lists[result_type] = {
        "items": list(items),
        "rid": rid,
        "start": datetime.datetime.now(),
        "clicks": {},
    }


def current_sid():
    """Return the STELLA session id of this user, or None if there is none or
    it expired. Any activity within the timeout keeps the session alive."""
    now = time.time()
    if session.get("sid") and now - session.get("last_seen", 0) > SESSION_TIMEOUT:
        logging.info("STELLA session %s expired", session["sid"])
        session.pop("sid", None)
    session["last_seen"] = now
    return session.get("sid")


def remember_sid(header):
    """Store the session id the STELLA app assigned (or confirmed)."""
    sid = (header or {}).get("sid")
    if sid:
        session["sid"] = sid
        session["last_seen"] = time.time()


def send_feedback(result_type, docid):
    """Record a click on `docid` in the given result list and send the
    accumulated, actual clicks for that list to the STELLA app."""
    state = result_lists.get(result_type)
    if state is None or state["rid"] is None:
        return
    if docid not in {item.get("docid") for item in state["items"]}:
        logging.warning("Clicked doc %s is not part of the current %s list", docid, result_type)
        return

    now = datetime.datetime.now()
    state["clicks"].setdefault(docid, now.strftime(DATE_FMT))

    # Rank positions are 1-based, matching the STELLA app API.
    click_dict = {}
    for rank, item in enumerate(state["items"], start=1):
        click_date = state["clicks"].get(item.get("docid"))
        click_dict[str(rank)] = {
            "docid": item.get("docid"),
            "type": item.get("type"),
            "clicked": click_date is not None,
            "date": click_date,
        }

    payload = {
        "start": state["start"].strftime(DATE_FMT),
        "end": now.strftime(DATE_FMT),
        "interleave": True,
        "clicks": json.dumps(click_dict),
    }

    endpoint = "ranking" if result_type == "RANK" else "recommendation"
    url = STELLA_APP_API + endpoint + "/" + str(state["rid"]) + "/feedback"
    try:
        feedback_req = requests.post(url, data=payload)
    except requests.RequestException as e:
        logging.error("Feedback request to %s failed: %s", url, e)
        return

    if feedback_req.status_code not in (200, 201):
        logging.error(
            "Feedback request failed with status code %s: %s",
            feedback_req.status_code,
            feedback_req.text,
        )
        return

    logging.info("FEEDBACK RESPONSE (%s %s): %s", endpoint, state["rid"], feedback_req.text)


class SearchForm(FlaskForm):
    query = StringField("", validators=[DataRequired()])
    submit = SubmitField("Search")


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "udonotknow")
bootstrap = Bootstrap()
bootstrap.init_app(app)


@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    form = SearchForm()

    try:
        if form.validate_on_submit():
            query = form.query.data
            form.query.data = query
            params = {"query": query}
            sid = current_sid()
            if sid:
                params["sid"] = sid
            req = requests.get(STELLA_APP_API + "ranking", params=params).json()
            if not req.get("header"):
                logging.error("Could not retrieve ranking for query: %s", query)
                return render_template("index.html", form=form, results=results)
            else:
                logging.info(req)

            remember_sid(req.get("header"))
            ranking_list = list(req.get("body").values())
            set_result_list("RANK", ranking_list, req.get("header").get("rid"))

            id_list = [doc["docid"] for doc in ranking_list]

            results = doc_list(id_list)

            logging.info("Retrieved %s results for query: %s", len(results), query)

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
    doc = publication_corpus.get(docid)
    params = {"itemid": docid}
    sid = current_sid()
    if sid:
        params["sid"] = sid
    req = requests.get(STELLA_APP_API + "recommendation", params=params)

    req = req.json()
    logging.info(req)
    remember_sid(req.get("header"))

    pub_ids = doc_list([v["docid"] for k, v in req.get("body").items()])

    set_result_list("REC_PUB", req.get("body").values(), req.get("header").get("rid"))

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
    send_feedback(result_type, docid)

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

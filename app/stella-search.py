import ast
import datetime
import json
import logging
import os
import pathlib
import sqlite3
import threading
import time
from contextlib import closing

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
# SQLite lookup store built from PUB_PATH; defaults to PUB_PATH + ".sqlite".
CORPUS_DB = os.environ.get("CORPUS_DB") or None

DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _field_candidates(env_var, default):
    """Comma-separated list of source field names, tried in order."""
    return [f.strip() for f in os.environ.get(env_var, default).split(",") if f.strip()]


# Mapping from the internal document schema to the field names of the corpus.
# Each entry lists source fields tried in order; the first non-empty one wins.
# Required: id, title, text. Optional: type, date, source, url.
FIELD_MAP = {
    "id": _field_candidates("ID_FIELD", "id,docid,_id"),
    "title": _field_candidates("TITLE_FIELD", "title"),
    "text": _field_candidates("TEXT_FIELD", "abstract,text,contents,body"),
    "type": _field_candidates("TYPE_FIELD", "type"),
    "date": _field_candidates("DATE_FIELD", "date"),
    "source": _field_candidates("SOURCE_FIELD", "source,publisher"),
    "url": _field_candidates("URL_FIELD", "url"),
}

# Length of the text snippet shown on the result page (full text on the detail page).
SNIPPET_LENGTH = int(os.environ.get("SNIPPET_LENGTH", 300))

# Whether the detail page requests recommendations from the STELLA app.
# Disable when the STELLA app has no recommender configured.
RECOMMENDATIONS_ENABLED = os.environ.get("RECOMMENDATIONS", "true").strip().lower() not in (
    "0", "false", "no", "off", "",
)

# A STELLA session (sid) ends after this many seconds without user activity.
SESSION_TIMEOUT = int(os.environ.get("SESSION_TIMEOUT", 5 * 60))

# State of the most recently shown result lists (single-user demo, module-level).
# Each entry holds the list returned by the STELLA app, its result id (rid),
# the time it was shown, and the clicks recorded on it so far (docid -> click date).
result_lists = {
    "RANK": {"items": [], "rid": None, "start": None, "clicks": {}},
    "REC_PUB": {"items": [], "rid": None, "start": None, "clicks": {}},
}


def _as_text(value):
    """Flatten a raw field value (str, number, list, ...) into a string."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_as_text(v) for v in value if v is not None).strip()
    return str(value).strip()


def _lookup(record, candidates):
    for field in candidates:
        value = _as_text(record.get(field))
        if value:
            return value
    return ""


def _snippet(text, length=SNIPPET_LENGTH):
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + " …"


def normalize_doc(record):
    """Map a raw corpus record onto the internal schema
    {id, title, text, snippet, type, date, source, url, meta}.
    Returns None if the record has no id."""
    doc = {key: _lookup(record, candidates) for key, candidates in FIELD_MAP.items()}
    if not doc["id"]:
        return None
    if not doc["title"]:
        doc["title"] = doc["id"]
    doc["snippet"] = _snippet(doc["text"])
    used = {f for candidates in FIELD_MAP.values() for f in candidates}
    doc["meta"] = {k: v for k, v in record.items() if k not in used}
    return doc


class CorpusStore:
    """Read-only id -> normalized doc lookup backed by an SQLite file.

    The JSONL corpus is normalized once into `<jl_path>.sqlite` (or `db_path`)
    and only rebuilt when the JSONL file or the field mapping changes, so the
    corpus never has to fit into memory and restarts are instant."""

    SCHEMA_VERSION = 1
    BATCH_SIZE = 10000

    def __init__(self, jl_path, db_path=None):
        self.jl_path = jl_path
        self.db_path = db_path or jl_path + ".sqlite"
        self._ready = False
        self._lock = threading.Lock()
        self._local = threading.local()

    def _signature(self):
        stat = os.stat(self.jl_path)
        return json.dumps({
            "schema": self.SCHEMA_VERSION,
            "size": stat.st_size,
            "mtime": stat.st_mtime_ns,
            "field_map": FIELD_MAP,
            "snippet_length": SNIPPET_LENGTH,
        }, sort_keys=True)

    def _stored_signature(self):
        if not os.path.exists(self.db_path):
            return None
        try:
            with closing(sqlite3.connect(self.db_path)) as con:
                row = con.execute("SELECT value FROM meta WHERE key = 'signature'").fetchone()
            return row[0] if row else None
        except sqlite3.Error:
            return None

    def ensure_ready(self):
        """Build the SQLite store if it is missing or stale. Safe to call repeatedly."""
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            if not os.path.exists(self.jl_path):
                logging.error("Corpus file %s not found (set PUB_PATH); results cannot be displayed",
                              self.jl_path)
            else:
                signature = self._signature()
                if self._stored_signature() != signature:
                    self._build(signature)
                else:
                    logging.info("Using corpus store %s", self.db_path)
            self._ready = True

    def _build(self, signature):
        logging.info("Building corpus store %s from %s (one-time, may take a while)",
                     self.db_path, self.jl_path)
        tmp_path = self.db_path + ".tmp"
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        indexed = skipped = with_text = 0
        with closing(sqlite3.connect(tmp_path)) as con:
            con.execute("PRAGMA journal_mode = OFF")
            con.execute("PRAGMA synchronous = OFF")
            con.execute("CREATE TABLE docs (id TEXT PRIMARY KEY, doc TEXT NOT NULL)")
            con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
            batch = []
            with open(self.jl_path) as jl:
                for line_no, line in enumerate(jl, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        doc = normalize_doc(json.loads(line))
                    except json.JSONDecodeError as e:
                        logging.warning("%s:%s is not valid JSON: %s", self.jl_path, line_no, e)
                        doc = None
                    if doc is None:
                        skipped += 1
                        continue
                    with_text += bool(doc["text"])
                    # Later records with the same id win, as before.
                    batch.append((doc["id"], json.dumps(doc)))
                    if len(batch) >= self.BATCH_SIZE:
                        con.executemany("INSERT OR REPLACE INTO docs VALUES (?, ?)", batch)
                        indexed += len(batch)
                        batch = []
                        if indexed % 100000 == 0:
                            logging.info("Indexed %s documents ...", indexed)
            con.executemany("INSERT OR REPLACE INTO docs VALUES (?, ?)", batch)
            indexed += len(batch)
            con.execute("INSERT INTO meta VALUES ('signature', ?)", (signature,))
            con.commit()
        # Swap in atomically so a crashed build never leaves a half-written store.
        os.replace(tmp_path, self.db_path)

        if skipped:
            logging.warning("Skipped %s records without id (fields tried: %s) in %s",
                            skipped, FIELD_MAP["id"], self.jl_path)
        if indexed and not with_text:
            logging.warning("No document has text (fields tried: %s); set TEXT_FIELD", FIELD_MAP["text"])
        logging.info("Indexed %s documents from %s", indexed, self.jl_path)

    def _connection(self):
        con = getattr(self._local, "con", None)
        if con is None:
            uri = pathlib.Path(self.db_path).resolve().as_uri() + "?mode=ro"
            con = sqlite3.connect(uri, uri=True)
            self._local.con = con
        return con

    def get(self, docid, default=None):
        self.ensure_ready()
        if docid is None or not os.path.exists(self.db_path):
            return default
        row = self._connection().execute(
            "SELECT doc FROM docs WHERE id = ?", (str(docid),)
        ).fetchone()
        return json.loads(row[0]) if row else default


def doc_list(id_list):
    """Resolve doc ids to corpus documents, dropping ids missing from the corpus."""
    docs = []
    for docid in id_list:
        doc = publication_corpus.get(docid)
        if doc is None:
            logging.warning("Doc %s returned by STELLA is not in the local corpus", docid)
            continue
        docs.append(doc)
    return docs


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
    """Fetch recommendations for `docid` from the STELLA app and return the
    top similar documents. Returns [] if recommendations are disabled or the
    STELLA app has none (e.g. no recommender configured), so the detail page
    still renders."""
    if not RECOMMENDATIONS_ENABLED:
        return []
    params = {"itemid": docid}
    sid = current_sid()
    if sid:
        params["sid"] = sid
    url = STELLA_APP_API + "recommendation"
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        req = resp.json()
    except (requests.RequestException, ValueError) as e:
        logging.error("Could not retrieve recommendations for %s from %s: %s", docid, url, e)
        return []

    logging.info(req)
    header, body = req.get("header") or {}, req.get("body") or {}
    remember_sid(header)
    if not body:
        return []

    set_result_list("REC_PUB", body.values(), header.get("rid"))
    return doc_list([v["docid"] for v in body.values()])[:3]


@app.route("/detail/<string:docid>/<string:result_type>", methods=["GET"])
def detail(docid, result_type):
    send_feedback(result_type, docid)

    document = publication_corpus.get(docid) or {"id": docid, "title": docid, "text": ""}
    similar_items = get_recommendations(docid)

    return render_template(
        "detail.html",
        document=document,
        similar_items=similar_items,
        show_recommendations=RECOMMENDATIONS_ENABLED,
        query=docid,
    )


publication_corpus = CorpusStore(PUB_PATH, CORPUS_DB)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # Build/validate the store before serving, not on the first request.
    publication_corpus.ensure_ready()
    if port == 5000:
        app.debug = True

    app.run(host="0.0.0.0", port=port)

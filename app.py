from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

import requests

app = Flask(__name__)
app.config['SECRET_KEY'] = 'udonotknow'
bootstrap = Bootstrap()
bootstrap.init_app(app)


class SearchForm(FlaskForm):
    query = StringField('', validators=[DataRequired()])
    submit = SubmitField('Search')


@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    form = SearchForm()
    if form.validate_on_submit():
        query = form.query.data
        form.query.data = query

        req = requests.get("http://0.0.0.0/stella/api/v1/ranking/" + query).json()

        results = list(req.values())

    return render_template('index.html', form=form, results=results)

@app.route('/detail/<string:doc_id>', methods=['GET'])
def detail(doc_id):
    
    
    req = requests.get("http://0.0.0.0/stella/api/v1/recommend_dataset/" + doc_id).json()
    print(req.values())
    results = list(req.values())
    
    return render_template('detail.html', results=req)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

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
    
def item_details(id):
    id_req = requests.get("http://193.175.238.15:5555/api/items/" + id).json()
    return(id_req)

@app.route('/detail/<string:doc_id>', methods=['GET'])

def detail(doc_id):
       
    req = requests.get("http://193.175.238.15:5555/api/recommand_dataset/" + doc_id).json()
    results = req
    l = {} 
    if results["container"] == "tf-idf-container" :
        for key in results['similar_items']:
            detail = item_details(key)
            if detail["type"] == "research_data" : 
                if "publisher" not in detail:
    #               l[key] = {"Title": detail["title"], "Id": detail["id"], "Date": detail["date"],"Publisher":detail["publisher"], "Type": detail["type"] }
                    l[key] = {"Title": detail["title"], "Id": detail["id"], "Date": detail["date"],"Publisher": "Unidentified", "Type": detail["type"] }
                else : 
                    l[key] = {"Title": detail["title"], "Id": detail["id"], "Date": detail["date"],"Publisher": detail["publisher"], "Type": detail["type"] }
    else : 
        for key in range(len(results['similar_items'])):
            o = (results['similar_items'][key][0]).encode('ascii', 'ignore')
            detail = item_details(o)
            if detail["type"] == "research_data" : 
                if "publisher" not in detail:
    #               l[key] = {"Title": detail["title"], "Id": detail["id"], "Date": detail["date"],"Publisher":detail["publisher"], "Type": detail["type"] }
                    l[o] = {"Title": detail["title"], "Id": detail["id"], "Date": detail["date"],"Publisher": "Unidentified", "Type": detail["type"] }
                else : 
                    l[o] = {"Title": detail["title"], "Id": detail["id"], "Date": detail["date"],"Publisher": detail["publisher"], "Type": detail["type"] }
            
            
    
    return render_template('detail.html', results=req, id_results = l , query = doc_id)



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

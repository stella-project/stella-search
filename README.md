# STELLA Search

A minimalistic search interface that connects to the STELLA infrastructure. 
Queries are conducted to the [STELLA app](https://github.com/stella-project/stella-app) (make sure it is running) and results will be returned. 
This example works best with the [elastic-wapo](https://github.com/stella-project/stella-app/tree/elastic-wapo) branch.

## Setup

1. Clone this repository:
```
git clone https://github.com/stella-project/stella-search.git
```

2. Install requirements:
```
pip install -r requirements.txt
```

3. Start app:
```
python app.py
```

4. Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/) and enter a query. The sample data @[elastic-wapo](https://github.com/stella-project/stella-app/tree/elastic-wapo) is taken from [Pitchfork reviews](https://www.kaggle.com/nolanbconaway/pitchfork-data/data), this means documents contain text related to music. Type something like `singer`, `guitar`, or `drums`.

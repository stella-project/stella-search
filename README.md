# STELLA Search
A search interface that connects to the STELLA infrastructure. Queries are conducted to the [STELLA app](https://github.com/stella-project/stella-app) and logged data can be investigated by visiting the dashboard service of the [STELLA server](https://github.com/stella-project/stella-server).

## Demo setup of the entire infrastructure
* Clone this repository:
```
git clone https://github.com/stella-project/stella-search.git
```

* Clone the [STELLA app](https://github.com/stella-project/stella-app):
```
git clone https://github.com/stella-project/stella-app.git
```

* Clone the [STELLA server](https://github.com/stella-project/stella-server):
```
git clone https://github.com/stella-project/stella-server.git
```
* Make sure the following ports are available `80`,`8000`, and `8080`. The STELLA server will run on port `80`, the STELLA app on port `8080` and the STELLA search interface on port `8000`.   
* Place the dataset you want to be indexed in `data/index` in both repositories [STELLA search](https://github.com/stella-project/stella-search) and [STELLA app](https://github.com/stella-project/stella-app). Per default we use the PubMed snapshot `livivo.jsonl` from 2015-2016 by LIVIVO. However, in this case no dataset recommendations can be provided. By using the `gesis.jsonl`, dataset recommendations are available but only in German. Likewise you can use you own dataset. In order to do so, you have to convert the data into the right format (see also this [script](https://github.com/stella-project/stella-search/blob/master/data/convert.py)).
* Start the STELLA server first in order to setup a docker network for all containers.
```
cd ./stella-server
docker-compose up -d
```
* Start the STELLA app:
```
cd ../stella-app
docker-compose -f local.yml up -d
```
* Index the data by visiting `0.0.0.0:8080` and click all index buttons. Alternatively, the indexing can be triggered by API endpoints.
* Start STELLA search:
```
cd ../stella-search
docker-compose up -d
```
* Visit [http://0.0.0.0:8000](http://0.0.0.0:8000) and enter a query, browse, click, ...
* Visit [http://0.0.0.0:80](http://0.0.0.0:80), login and visit the dashboard. Use the following credentials for a pre-registered account:  
`user`: site_a@stella.org  
`pass`: pass  
Alternatively, you can simulate user interactions with the script provided in the STELLA server repository.

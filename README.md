# STELLA Search

[Demo setup of the entire infrastructure](https://github.com/stella-project/stella-search#demo-setup-of-the-entire-infrastructure)

A search interface that connects to the STELLA infrastructure. Queries are conducted to the [STELLA app](https://github.com/stella-project/stella-app) and logged data can be investigated by visiting the dashboard service of the [STELLA server](https://github.com/stella-project/stella-server).

## Demo setup of the entire infrastructure
The following setup guide can be used to get the entire infrastructure running with less than 10 command line calls. Required are installations of docker and docker-compose and the possibility to run docker as a non-root user.

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
docker-compose -f stella-server/docker-compose.yml up -d
```
* Start the STELLA app:
```
docker-compose -f stella-app/docker-compose.yml up -d
```
When setting up the STELLA app, the data will be indexed by each system. For these sample datasets this is managable by a laptop. If the datasets get larger, you can start the indexing of single containers by visiting [http://0.0.0.0:8080](http://0.0.0.0:8080) and clicking the index buttons. Likewise, the indexing can be triggered by API endpoints for either single containers or bulk/parallel indexing.
* Start STELLA search:
```
docker-compose -f stella-search/docker-compose.yml up -d
```
* Visit [http://0.0.0.0:8000](http://0.0.0.0:8000) and enter a query, browse, click. As the demo includes a small sample dataset from the medical domain try queries like `vaccine`, `treatment`, `epidemic`.
* Visit [http://0.0.0.0:80](http://0.0.0.0:80), login and visit the dashboard. Use the following credentials for a pre-registered account:  
`user`: site_a@stella.org  
`pass`: pass  
Alternatively, you can simulate user interactions with the script provided in the STELLA server repository.


## Citation

If you use `stella-search` in your work, please refer to it by the `CITATION.cff` file:


```
# YAML 1.2
---
abstract: "STELLA search is a minimal front-end that is used to showcase the idea of the STELLA infrastructure. It offers access to results from the STELLA app and, likewise, sends feedback to it. It includes a search field, a dynamic list of found results and a detail view with recommendations."
authors: 
  -
    affiliation: "TH Köln - University of Applied Sciences, Germany"
    family-names: Schaer
    given-names: Philipp
    orcid: "https://orcid.org/0000-0002-8817-4632"
  -
    affiliation: "GESIS - Leibniz Institute for the Social Sciences, Germany"
    family-names: Schaible
    given-names: Johann
    orcid: "https://orcid.org/0000-0002-5441-7640"
  -
    affiliation: "ZB MED - Information Centre for Life Sciences, Germany"
    family-names: "Garcia Castro"
    given-names: "Leyla Jael"
    orcid: "https://orcid.org/0000-0003-3986-0510"
  -
    affiliation: "TH Köln - University of Applied Sciences, Germany"
    family-names: Breuer
    given-names: Timo
    orcid: "https://orcid.org/0000-0002-1765-2449"
  -
    affiliation: "GESIS - Leibniz Institute for the Social Sciences, Germany"
    family-names: Tavakolpoursaleh
    given-names: Narges
    orcid: "https://orcid.org/0000-0001-9324-3252"
  -
    affiliation: "ZB MED - Information Centre for Life Sciences, Germany"
    family-names: Wolff
    given-names: Benjamin
    orcid: "https://orcid.org/0000-0001-9345-8958"
cff-version: "1.1.0"
date-released: 2020-09-21
keywords: 
  - "Living Lab"
  - "Evaluation Infrastructure"
  - "Shared Task"
license: MIT
message: "If you use this software, please cite it using these metadata."
title: "STELLA Search"
version: "0.1"
...
```

## License

`stella-search` is licensed under the MIT license. If you modify `stella-search` in any way, please link back to this repository.

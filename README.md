# STELLA Search

[Demo setup of the entire infrastructure](https://github.com/stella-project/stella-search#demo-setup-of-the-entire-infrastructure)

A search interface that connects to the STELLA infrastructure. Queries are conducted to the [STELLA app](https://github.com/stella-project/stella-app) and logged data can be investigated by visiting the dashboard service of the [STELLA server](https://github.com/stella-project/stella-server).

## Demo setup of the entire infrastructure
The following setup guide can be used to get the entire infrastructure running with less than 10 command line calls. Required are installations of docker and docker-compose and the possibility to run docker as a non-root user.

* Clone [STELLA Search](https://github.com/stella-project/stella-search):
```
git clone https://github.com/stella-project/stella-search.git && cd stella-search && git checkout 0bfc0f9ec17d80a1f4287409adce8f9ee94f1a52 && cd ..
```

* Clone the [STELLA app](https://github.com/stella-project/stella-app):
```
git clone https://github.com/stella-project/stella-app.git && cd stella-app && git checkout 0686a402103e9e8db8eb3268886aac1f6cc7aff6 && cd ..
```

* Clone the [STELLA server](https://github.com/stella-project/stella-server):
```
git clone https://github.com/stella-project/stella-server.git && cd stella-server && git checkout 054cc2e03faadffb7aada1f94663176fb075fd08 && cd ..
```
* Make sure the following ports are available `80`,`8000`, and `8080`. The STELLA server will run on port `80`, the STELLA app on port `8080` and the STELLA search interface on port `8000`.   
* Place the dataset you want to be indexed in `data/index` in both repositories [STELLA search](https://github.com/stella-project/stella-search) and [STELLA app](https://github.com/stella-project/stella-app). Per default we use the PubMed snapshot `livivo.jsonl` from 2015-2016 by LIVIVO. This means, if you are fine with using this data, you do not have to mv/cp/rm anything to/from the data folders (do not touch it!). However, in this case no dataset recommendations can be provided. By using the `gesis.jsonl`, dataset recommendations are available but only in German. Likewise you can use you own dataset. In order to do so, you have to convert the data into the right format (see also this [script](https://github.com/stella-project/stella-search/blob/master/data/convert.py)).
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

We provide citation information via the [CITATION file](./CITATION.cff). If you use `stella-search` in your work, please cite our repository as follows:

> Schaer P, Schaible J, Garcia Castro LJ, Breuer T, Tavakolpoursaleh N, Wolff B. STELLA Search. Available at https://github.com/stella-project/stella-search/

We recommend you include the retrieval date.

## License

`stella-search` is licensed under the [GNU GPLv3 license](https://github.com/stella-project/stella-search/blob/master/LICENSE). If you modify `stella-search` in any way, please link back to this repository.

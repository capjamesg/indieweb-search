# IndieWeb Search Engine

This repository contains the source code for the indieweb-search crawler and web application.

All files in the crawler/ directory relate to the web crawler. All files in the main directory relate to the web application.

The search engine is available at [https://indieweb-search.jamesg.blog](indieweb-search.jamesg.blog).

## Installation Instructions

You can install the required dependencies to run this project by running the following command:

    pip install -r requirements.txt

You may encounter errors when setting up the project that ask you to install nltk or spacy models.

Please read these errors individually and install the packages according to the instructions in the error message.

Documentation on exactly what to install will follow in the future.

## Running the Web Application

To run the web application, execute these commands:

    export FLASK_APP=.
    flask seed build-tables
    flask run

The search engine will not be available until you have indexed some content.

You can do this by adding a site URL to the crawl_queue.txt file and then running this command:

    python3 build_index.py

Your site URL will be removed from the crawl_queue.txt file after your site has been fully crawled.

All crawls are limited to 1000 URLs. To change this limit, search for "1000" in the crawler/url_handling.py file and change the value to the desired limit.

## License

This project is licensed under the [MIT license](LICENSE).

## Adding Your Domain to the Index

This repository does not contain a list of any domains indexed in the live search engine.

If you would like to request your site be indexed on indieweb-search.jamesg.blog, please create an issue on this project.

Only contributors to the IndieWeb wiki will be considered at this stage due to the limited compute resources available for this project.

## Contributors

- capjamesg
# IndieWeb Search Engine

This repository contains the source code for the IndieWeb Search crawler, web application, and back-end server.

The search engine is available at [indieweb-search.jamesg.blog](https://indieweb-search.jamesg.blog).

This document contains the main documentation for IndieWeb Search.

Further high-level project notes on the search engine is available on the [IndieWeb wiki](https://indieweb.org/IndieWeb_Search).

## Screenshot

![IndieWeb search engine home page](screenshot.png)

## Installation Instructions

You can install the required dependencies to run this project by running the following command:

    pip install -r requirements.txt

You may encounter errors when setting up the project that ask you to install nltk or spacy models.

Please read these errors individually and install the packages according to the instructions in the error message.

Documentation on exactly what to install will follow in the future.

## Site Search Support

IndieWeb Search supports searching sites by URL. Read the [Advanced Settings documentation](https://indieweb-search.jamesg.blog/advanced) for information on how to search for a page on a specific website.

## Indexing Content

You can do this by adding a site URL to the `crawl_queue.txt` file and then running this command:

    python3 build_index.py

All content will be saved to `results.json`. This means you can index without having your own Elasticsearch server running.

Your site URL will be removed from the `crawl_queue.txt` file after your site has been fully crawled.

All crawls are limited to 1,000 URLs. To change this limit, search for "1000" in the `crawler/url_handling.py` file and change the value to the desired limit.

You can run the crawler in the background using this command:

    nohup python3 build_index.py &

Running the crawler in the background is only recommended once you have crawled at least one site and made sure you have not encountered any errors.

### Configuration

Please create a `config.py` file in the root directory of this project before running the application for the first time.

The config.py file should contain the following variables:

    import os

    HEADERS = {
        "User-agent": "indieweb-search",
        "Accept": "text/html, application/xhtml+xml, text/xml, */*" # used for content negotiation
    }

    ROOT_DIRECTORY = os.path.dirname(os.path.abspath("__init__.py"))

    SECRET_KEY = os.urandom(24)

    ELASTICSEARCH_PASSWORD = "YOUR_ELASTICSEARCH_PASSWORD"

    ELASTICSEARCH_API_TOKEN = "YOUR_ELASTICSEARCH_API_TOKEN"

    MYSQL_DB_USER = "YOUR_MYSQL_DB_USERNAME"

    MYSQL_DB_PASSWORD = "YOUR_MYSQL_DB_PASSWORD"

The official indieweb-search engine uses indieweb-search as the user agent. Please choose another user agent if you use this crawler.

## Running the Web Application

To run the web application, execute these commands:

    export FLASK_APP=.
    flask seed build-tables
    flask run

You will not be able to run the web application without having a server running the `elasticsearch_server.py` that has some indexed files.

## Running the Elasticsearch Application

This project uses Elasticsearch for indexing content. To make use of the Elasticsearch back-end server provided by this project -- which is integrated into many of the ingestion and helper scripts -- please install Elasticsearch and run the `elasticsearch_server.py` file as a web server.

You should have a copy of your `config.py` file in the root directory of your Elasticsearch web server. This is important because the Elasticsearch web server provided by this application relies on many of the same configuration values in the `config.py` file that the main application uses.

You will also need MySQL installed on the same server you use to run your Elasticsearch web server.

With MySQL and Elasticsearch installed, run the following command on your Elasticsearch web server:

    python3 seed.py

This command will seed the MySQL database with the tables you need to run the web server.

Now you are ready to run the `elasticsearch_server.py` script:

    python3 elasticsearch_server.py

## Project Architecture

This project is divided into a few different folders. Each folder corresponds to a separate part of the IndieWeb Search engine.

Here is a list of all the folders in this project that are relevant to running this project:

- crawler/: This folder contains the modules that handle crawling web pages. The code in this folder is invoked by build_index.py in the main folder.
- direct_answers/: Code that handles direct answers to questions at the top of search results.
- elasticsearch_server/: The back-end code that runs the project Elasticsearch server. This server MUST be deployed on the same server on which your Elasticsearch cluster is running.
- elasticsearch_helpers/: Helper scripts used to interact with Elasticsearch. Most of these scripts relate to cleaning up the search index, deriving insights from the content in the index, and past experiments. The most used file in this folder is links.py which builds the project link index.
- legacy/: Code from the previous iteration of this project. Preserved just in case it is needed again in the future.
- logs/: Where all crawl logs are kept. This folder is not committed. You should create a logs folder before you run the crawler for the first time.
- static/: Static assets to be served by the front-end web application.
- templates/: HTML templates for the front-end of the web application.
- Main folder (root): This folder contains the main code for the project.

### Main Folder Key Files

The main folder contains root files that are relevant to running the project. These are:

- recrawl.py: Start a recrawl.
- main.py: Run the web application.
- build_index.py: The program that starts the web crawler.

## Direct Answer Search Results

Work is being done to support some "direct answer" search results. These are search results that aim to provide an immediate answer to your query before you click on a search result.

The main "direct answers" that are in development are:

- Answering questions with an answer (triggered by `what is [your query]`). This type of direct answer currently relies on answers from the IndieWeb wiki.
- Showing the h-card of a domain (triggered by `who is [domain-name]`).
- Identifying names of people, places, and organizations.
    - This is a long-term project and only source code from capjamesg's personal search engine is currently in the project.
- Showing recipes marked up with h-recipe.
- Showing reviews marked up with h-review.
- Showing events marked up with h-event.
- Displaying feeds associated with a page.
- Showing all rel=me links on a site's home page.

## Adding Your Domain to the Index

This repository does not contain a list of any domains indexed in the live search engine.

If you would like to request your site be indexed on indieweb-search.jamesg.blog, please create an issue on this project.

Only contributors to the IndieWeb wiki will be considered at this stage due to the limited compute resources available for this project.

## Search Result API

Results pages from IndieWeb Search are programmatically accessible in two ways:

1. By using one of the search result feeds, as mentioned in the "Supported Feeds" section of this document.
2. By using the dedicated JSON API flags in the URL of a results page.

To find out more information about a result, including the raw text stored in the index that corresponds to the result, we recommend using the API.

### Supported Feeds

All IndieWeb Search results are marked up with a h-feed containing h-entry objects. This means you can subscribe to any search results page in a feed reader that can process h-feed. In addition, the following feed types are supported:

- [jf2 Feed](https://indieweb.org/jf2)
- [JSON Feed](https://www.jsonfeed.org)
- RSS Feed

### Feed API

You can also use the custom JSON API which contains more granular search information. The data in the JSON API is *not* JSON Feed data as per the [JSON Feed](https://www.jsonfeed.org) specification. Instead, the JSON API is a custom JSON object that contains more information than other forms of structured data allow.

To use the JSON API, append one of the two flags below to the end of a search result URL:

- `format=direct_serp_json`: Returns the featured snippet displayed in the search result. No more than one featured snippet will be returned.
- `format=results_page_json`: Returns all results displayed in the search result, excluding the featured snippet result.

Here is an example JSON API call:

    https://indieweb-search.jamesg.blog/results?query=what+is+a+web+crawler&format=results_page_json

This API call returns:

- category
- domain
- h1
- h2
- h3
- incoming_links (integer)
- length (whole document length)
- meta_description
- outgoing_links (integer)
- published_on (not always available)
- title
- url
- word_count (integer)

## Discovery APIs

IndieWeb Search has open APIs that implement the authorship discovery and post type discovery IndieWeb specifications. You can access these APIs to find the original author of a post and the type of a post, respectively/

### Post Type API

The post type API can be accessed by making the following API call:

    /api/post_type?url=URL

Where URL is equal to the URL whose post type you want to discover.

A successful API call will return a JSON object with the following properties:

    {
        "status": "success",
        "result": "post_type (i.e. 'like')"
    }

A failed API call will return the following response:

    {
        "status": "failed",
        "message": "An error message",
        "result: ""
    }

### Authorship Discovery API

The authorship discovery API returns a h-card for the author who wrote a post.

A successful API call will return:

    {
        "status": "success",
        "result": {
            "name": "Author Name",
            "url": "https://author.example.com",
            "photo": "https://author.example.com/photo.jpg",
            "summary": "Author summary",
            "h-card": {
                "name": "Author Name",
                "url": "https://author.example.com",
                "photo": "https://author.example.com/photo.jpg",
                "summary": "Author summary"
            }
        }
    }

A failed API call will return:

    {
        "status": "failed",
        "message": "An error message",
        "result": []
    }

## Rich Results

IndieWeb Search may return a rich result for a site. This can happen under a number of circumstances. For example, if a site has a h-card, the h-card will be returned as a rich result in response to a "who is" query. Or if a page is marked up as h-review and a user looks for a review, the review might be returned as a rich result.

Only one rich result can appear per query.

To maximise your chances of getting a rich result, we recommend using semantic HTML in your code.

Some rich results are only available if you use microformats in your code.

These are:

- Reviews: use h-review for a chance to get a rich result for a review.
- Events: use h-event for a chance to get a rich result for an event description.
- Profiles: use h-card for a chance to get a rich result in response to a "who is" query. The h-card must be on your home page.
- Recipes: use h-recipe for a chance to get a rich result for a recipe.

## Recrawling

Recrawling sites is currently in development.

At the moment, this project collects all feeds from a site during a crawl and saves the feeds to the feeds.json file. These feeds are then read in the recrawl.py script which can be executed on demand. The recrawl script looks for any new items in the feed and then indexes them. In addition, the recrawl script looks through all indexed sitemaps and will index the URLs in them. This will help keep more content on a site fresh and ensure that most new pages are discovered and indexed without having to run a full recrawl.

This script is currently set up to run once per day via a cron job on the main project server.

The following feed types can be read by the recrawl script:

- JSON Feed (see [jsonfeed.org](https://jsonfeed.org) for more information)
- RSS feeds
- Atom feeds
- Microformats h-feeds (see [h-feed](https://microformats.org/wiki/h-feed) for more information)

Contributions related to recrawling are greatly appreciated as this is an active part of the project that has not yet been solved.

## Contributing

Feel free to contribute to this project no matter how much background you have in search.

Please refer to the Issues page in this repository for a list of features which have been proposed and bugs that need fixed. You can propose your own feature or help work on an existing request.

If you think something is missing from IndieWeb Search that would help you and potentially others, feel free to try your hand at implementing your idea.

## Technology Stack

This project makes use of the following technologies:

- Python
- Flask
- Elasticsearch
- mf2py
- BeautifulSoup
- Spacy
- Textblob
- pytextrank
- pyspellchecker
- feedparser
- indieweb_utils

## Acknowledgements

Thank you to [@snarfed](https://github.com/snarfed) for putting together [IndieMap](https://github.com/snarfed/indie-map), a project that crawled many IndieWeb sites to create a social graph. IndieMap provided inspiration, motivation, and a list of domains from which this project started indexing.

Thank you also to every member of the IndieWeb community. The support from community members is helping to make this search engine more effective.

### Icon Set Attribution

All icons used in featured snippets for "rel me" queries are from Paul Robert Lloyd's [socialmediaicons](https://github.com/paulrobertlloyd/socialmediaicons) repository. These icons are used in accordance with the Creative Commons Attribution-Share Alike 3.0 license under which the icons are licensed. Appropriate attribution is also listed on search pages where the icon set is used.

## License

This project is licensed under the [MIT license](LICENSE).

## Contributors

- capjamesg
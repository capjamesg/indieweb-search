Direct Answers: Getting Fast Answers to Queries
===============================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

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

The code for the logic used to retrieve direct answers from HTML documents is in the `direct_answers` folder.

Below is the documentation for each direct answer function in the repository.
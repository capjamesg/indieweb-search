from dataclasses import dataclass


@dataclass
class DirectAnswer:
    """
    A direct answer to a searcher's query.
    """

    answer_html: str
    answer_type: str
    breadcrumb: str
    title: str
    context: str = ""
    featured_image: str = ""

from nltk.stem.wordnet import WordNetLemmatizer


def lemmatize_content(page_content):
    lemmatizer = WordNetLemmatizer()

    if type(page_content) == list:
        return [lemmatizer.lemmatize(word) for word in page_content]
    else:
        return "".join([lemmatizer.lemmatize(word) for word in page_content.split()])

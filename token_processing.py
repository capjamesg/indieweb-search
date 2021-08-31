import spacy

nlp = spacy.load('en_core_web_sm')

doc = nlp("What equipment does fortitude coffee use?")

# remove all the stop words
without_stopwords = [token for token in doc if not token.is_stop]
remove_punctuation = [token.text for token in without_stopwords if not token.is_punct]

print(remove_punctuation)
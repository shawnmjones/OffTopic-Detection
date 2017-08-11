from abc import ABCMeta, abstractmethod

class TopicModel(metaclass=ABCMeta):

    def __init__(self, threshold, metadata):
        self.threshold = threshold
        self.metadata = metadata

    def tokenize(self):
        pass

    def load_stop_words(self):
        pass

    def stemming(self):
        pass

    @abstractmethod
    def get_scores(self):
        pass

class WordCountAgainstSingleResource(TopicModel):

    def __init__(self, threshold, metadata):
        raise NotImplementedError("WordCount is not available yet!")

    def get_scores(self):
        pass

class CosineSimilarityAgainstSingleResource(TopicModel):

    def __init__(self, threshold, metadata):
        raise NotImplementedError("Cosine Similarity is not available yet!")

    def get_scores(self):
        pass

class JaccardDistanceAgainstSingleResource(TopicModel):

    def __init__(self, threshold, metadata):
        raise NotImplementedError("Jaccard Distance not available yet!")

    def get_scores(self):
        pass
   
supported_measures = {
    'cosine': {
        'name': 'Cosine Similarity',
        'default_threshold': 0.15,
        'class': CosineSimilarityAgainstSingleResource
    },
    'jaccard': {
        'name': 'Jaccard Distance',
        'default_threshold': 0.10,
        'class': JaccardDistanceAgainstSingleResource
    },
    'wcount': {
        'name': 'Word Count',
        'default_threshold': -0.10,
        'class': WordCountAgainstSingleResource
    }
}

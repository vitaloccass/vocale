from elasticsearch import Elasticsearch
from datetime import datetime
import json

class ElasticsearchManager:
    def __init__(self, host='localhost', port=9200):
        self.es = Elasticsearch([f'http://{host}:{port}'])
        
    def create_index(self, index_name, mapping):
        """Créer un index avec mapping"""
        if self.es.indices.exists(index=index_name):
            print(f"L'index {index_name} existe déjà")
            return False
        
        self.es.indices.create(index=index_name, body=mapping)
        print(f"Index {index_name} créé avec succès")
        return True
    
    def index_document(self, index_name, doc_id, document):
        """Indexer un document"""
        response = self.es.index(
            index=index_name,
            id=doc_id,
            document=document
        )
        return response
    
    def search(self, index_name, query):
        """Effectuer une recherche"""
        response = self.es.search(index=index_name, body=query)
        return response
    
    def get_document(self, index_name, doc_id):
        """Récupérer un document par ID"""
        try:
            doc = self.es.get(index=index_name, id=doc_id)
            return doc['_source']
        except Exception as e:
            print(f"Erreur: {e}")
            return None
    
    def update_document(self, index_name, doc_id, updates):
        """Mettre à jour un document"""
        self.es.update(
            index=index_name,
            id=doc_id,
            body={'doc': updates}
        )
    
    def delete_document(self, index_name, doc_id):
        """Supprimer un document"""
        self.es.delete(index=index_name, id=doc_id)
    
    def delete_index(self, index_name):
        """Supprimer un index"""
        if self.es.indices.exists(index=index_name):
            self.es.indices.delete(index=index_name)
            print(f"Index {index_name} supprimé")

# Utilisation
if __name__ == '__main__':
    manager = ElasticsearchManager()
    
    # Créer un index
    mapping = {
        "mappings": {
            "properties": {
                "titre": {"type": "text", "analyzer": "french"},
                "contenu": {"type": "text", "analyzer": "french"},
                "auteur": {"type": "keyword"},
                "date": {"type": "date"},
                "vues": {"type": "integer"}
            }
        }
    }
    
    manager.create_index('articles', mapping)
    
    # Indexer des documents
    articles = [
        {
            'titre': 'Introduction à Elasticsearch',
            'contenu': 'Elasticsearch est un moteur de recherche distribué...',
            'auteur': 'Jean Dupont',
            'date': datetime.now().isoformat(),
            'vues': 150
        },
        {
            'titre': 'Python et Elasticsearch',
            'contenu': 'Utiliser Python avec Elasticsearch est très simple...',
            'auteur': 'Marie Martin',
            'date': datetime.now().isoformat(),
            'vues': 200
        }
    ]
    
    for i, article in enumerate(articles):
        manager.index_document('articles', f'article_{i}', article)
    
    # Rechercher
    query = {
        'query': {
            'match': {
                'contenu': 'elasticsearch python'
            }
        }
    }
    
    results = manager.search('articles', query)
    print(f"\nNombre de résultats: {results['hits']['total']['value']}")
    
    for hit in results['hits']['hits']:
        print(f"\nTitre: {hit['_source']['titre']}")
        print(f"Score: {hit['_score']}")
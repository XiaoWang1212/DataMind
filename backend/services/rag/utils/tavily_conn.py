
import logging
from tavily import TavilyClient
from src.utils import get_uuid
from src.rag.nlp import rag_tokenizer


class Tavily:
    def __init__(self, api_key: str):
        self.tavily_client = TavilyClient(api_key=api_key)

    def search(self, query):
        try:
            response = self.tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=6
            )
            return [{"url": res["url"], "title": res["title"], "content": res["content"], "score": res["score"]} for res in response["results"]]
        except Exception as e:
            logging.exception(e)

        return []

    def retrieve_chunks(self, question):
        chunks = []
        aggs = []
        logging.info("[Tavily]Q: " + question)
        for r in self.search(question):
            id = get_uuid()
            chunks.append({
                "chunk_id": id,
                "content_ltks": rag_tokenizer.tokenize(r["content"]),
                "content_with_weight": r["content"],
                "doc_id": id,
                "docnm_kwd": r["title"],
                "kb_id": [],
                "important_kwd": [],
                "image_id": "",
                "similarity": r["score"],
                "vector_similarity": 1.,
                "term_similarity": 0,
                "vector": [],
                "positions": [],
                "url": r["url"]
            })
            aggs.append({
                "doc_name": r["title"],
                "doc_id": id,
                "count": 1,
                "url": r["url"]
            })
            logging.info("[Tavily]R: "+r["content"][:128]+"...")
        return {"chunks": chunks, "doc_aggs": aggs}
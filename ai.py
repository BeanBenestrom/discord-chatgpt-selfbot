# External modules
import openai, os
from vector_database import _DIM
from random import random

# Internal modules
from utility import batch_iterator

# openai.api_key = os.environ["API_KEY_OPENAI"]
EMBEDDING_MAX_TOKENS     = 8191
EMBEDDING_MAX_BATCH_SIZE = 1000
# EMBEDDING_MAX_TOKEN_SIZE = 7800         # 100 tokens ~= 75 words, hence  tokens = 1.33333333333333333333333 * words
RPM = 20 
TPM = 150000

MAX_TOKENS = 4096



def embed_strings(strings: list[str]) -> list[list[float]]:
    # embeddings: list[list[float]] = []
    # tokens: int = 0

    # for batch in batch_iterator(strings, EMBEDDING_MAX_BATCH_SIZE):
    #     response = openai.Embedding.create(model="text-embedding-ada-002", input = batch) 
    #     tokens += response["usage"]["total_tokens"]     # type: ignore

    #     for embeddingObj in response["data"]:           # type: ignore
    #         embeddings.append(embeddingObj["embedding"])     

    # return embeddings
    return [[random()*2-1 for i in range(_DIM)] for j in range(len(strings)) ]


def openai_generate_response(message : str) -> str:
    # response = openai.ChatCompletion.create(
    #     model       =   "gpt-3.5-turbo",
    #     messages    =   [{"role": "user", "content": message}],
    #     temperature =   0.5)

    # return response["choices"][0]["message"]["content"] # type: ignore
    return "Cool!"


if __name__ == "__main__":
    pass
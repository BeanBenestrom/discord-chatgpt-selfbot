# External modules
import openai, os, asyncio
from vector_database import _DIM
from random import random

# Internal modules
from utility import batch_iterator, Result
from debug import LogHanglerInterface, LogNothing, LogType

openai.api_key = os.environ["API_KEY_OPENAI"]
EMBEDDING_MAX_TOKENS     = 8191
EMBEDDING_MAX_BATCH_SIZE = 1000
# EMBEDDING_MAX_TOKEN_SIZE = 7800         # 100 tokens ~= 75 words, hence  tokens = 1.33333333333333333333333 * words
RPM = 20 
TPM = 150000

MAX_TOKENS = 4096



async def embed_strings(strings: list[str], log: LogHanglerInterface=LogNothing()) -> Result[list[list[float]]]:
    embeddings: list[list[float]] = []
    tokens: int = 0

    try:
        for batch in batch_iterator(strings, EMBEDDING_MAX_BATCH_SIZE):
            response = await asyncio.get_event_loop().run_in_executor(None, lambda _ : openai.Embedding.create(model="text-embedding-ada-002", input = batch), "param")
            tokens += response["usage"]["total_tokens"]     # type: ignore

            for embeddingObj in response["data"]:           # type: ignore
                embeddings.append(embeddingObj["embedding"])     

        log.log(LogType.INFO, f"EMBEDDING TOKENS: {tokens}")
        return Result.ok(embeddings)
    except Exception as e:
        log.log(LogType.ERROR, f"Failed to generate embedding(s)!\nerror: {e}")
        log.log(LogType.INFO, f"EMBEDDING TOKENS: {tokens}")
        return Result.err(e)
    # return [[random()*2-1 for i in range(_DIM)] for j in range(len(strings)) ]


async def openai_generate_response(message : str, log: LogHanglerInterface=LogNothing()) -> Result[str]:
    try:
        response = await asyncio.get_event_loop().run_in_executor(None, lambda _ : openai.ChatCompletion.create(
            model       =   "gpt-3.5-turbo",
            messages    =   [{"role": "user", "content": message}],
            temperature =   0.5), "param")
        
        prompt_tokens       = response['usage']['prompt_tokens']        # type: ignore
        completion_tokens   = response['usage']['completion_tokens']    # type: ignore
        total_tokens        = response['usage']['total_tokens']         # type: ignore

        log.log(LogType.INFO, f"RESPONSE TOKENS:\nprompt  : {prompt_tokens}\nresponse: {completion_tokens}\ntotal   : {total_tokens}")
        return Result.ok(response["choices"][0]["message"]["content"])  # type: ignore
    except Exception as e:
        log.log(LogType.ERROR, f"Failed to generate response!\nerror: {e}")
        return Result.err(e)
    # return "Cool!"


if __name__ == "__main__":
    async def main():
        response = (await openai_generate_response("Hello, World!")).unwrap_or("FAILED TO UNWRAP")
        print(response)

    asyncio.run(main())
import pytest
from structure import Message
from prompt import TextModelInterface, DefaultTextModel, GeneratedConversation


@pytest.fixture()
def text_models() -> list[TextModelInterface]:
    return [DefaultTextModel()]


@pytest.fixture()
def test_messages() -> list[Message]:
    return [
        Message(1 , "2019-11-22 18:32:20.461000" , "Josh"       , "Hi"              ),
        Message(2 , "2019-12-01 00:15:31.402000" , "Dylan"      , "Hola"            ),
        Message(3 , "2019-12-01 00:15:53.088000" , "Dylan"      , "Hi"              ),
        Message(4 , "2019-12-01 00:16:14.233000" , "Josh"       , "Whatch up bros!" ),
        Message(5 , "2019-12-01 00:16:21.961000" , "Mike"       , "Sutt up!"        ),
        Message(6 , "2019-12-01 00:16:39.359000" , "Mike"       , "jk"              ),
        Message(7 , "2019-12-01 00:16:53.839000" , "Dylan"      , "Alright"         ),
        Message(8 , "2019-12-01 00:17:02.861000" , "Josh"       , "???"             ),
        Message(9 , "2019-12-01 00:17:23.229000" , "Mike"       , ":)"              ),
        Message(10, "2019-12-01 00:17:58.811000" , "Jessica"    , "Hi guys!"        ),
        Message(11, "2019-12-01 00:18:59.029000" , "Mike"       , "Shut up!"        ),
        Message(1 , "2019-11-22 18:32:20.461000" , "Josh"       , "Hi"              ),
        Message(2 , "2019-12-01 00:15:31.402000" , "Dylan"      , "Hola"            ),
        Message(3 , "2019-12-01 00:15:53.088000" , "Dylan"      , "Hi"              ),
        Message(4 , "2019-12-01 00:16:14.233000" , "Josh"       , "Whatch up bros!" ),
        Message(5 , "2019-12-01 00:16:21.961000" , "Mike"       , "Sutt up!"        ),
        Message(6 , "2019-12-01 00:16:39.359000" , "Mike"       , "jk"              ),
        Message(7 , "2019-12-01 00:16:53.839000" , "Dylan"      , "Alright"         ),
        Message(8 , "2019-12-01 00:17:02.861000" , "Josh"       , "???"             ),
        Message(9 , "2019-12-01 00:17:23.229000" , "Mike"       , ":)"              ),
        Message(10, "2019-12-01 00:17:58.811000" , "Jessica"    , "Hi guys!"        ),
        Message(11, "2019-12-01 00:18:59.029000" , "Mike"       , "Shut up!"        ),
        Message(1 , "2019-11-22 18:32:20.461000" , "Josh"       , "Hi"              ),
        Message(2 , "2019-12-01 00:15:31.402000" , "Dylan"      , "Hola"            ),
        Message(3 , "2019-12-01 00:15:53.088000" , "Dylan"      , "Hi"              ),
        Message(4 , "2019-12-01 00:16:14.233000" , "Josh"       , "Whatch up bros!" ),
        Message(5 , "2019-12-01 00:16:21.961000" , "Mike"       , "Sutt up!"        ),
        Message(6 , "2019-12-01 00:16:39.359000" , "Mike"       , "jk"              ),
        Message(7 , "2019-12-01 00:16:53.839000" , "Dylan"      , "Alright"         ),
        Message(8 , "2019-12-01 00:17:02.861000" , "Josh"       , "???"             ),
        Message(9 , "2019-12-01 00:17:23.229000" , "Mike"       , ":)"              ),
        Message(10, "2019-12-01 00:17:58.811000" , "Jessica"    , "Hi guys!"        ),
        Message(11, "2019-12-01 00:18:59.029000" , "Mike"       , "Shut up!"        ),
        Message(1 , "2019-11-22 18:32:20.461000" , "Josh"       , "Hi"              ),
        Message(2 , "2019-12-01 00:15:31.402000" , "Dylan"      , "Hola"            ),
        Message(3 , "2019-12-01 00:15:53.088000" , "Dylan"      , "Hi"              ),
        Message(4 , "2019-12-01 00:16:14.233000" , "Josh"       , "Whatch up bros!" ),
        Message(5 , "2019-12-01 00:16:21.961000" , "Mike"       , "Sutt up!"        ),
        Message(6 , "2019-12-01 00:16:39.359000" , "Mike"       , "jk"              ),
        Message(7 , "2019-12-01 00:16:53.839000" , "Dylan"      , "Alright"         ),
        Message(8 , "2019-12-01 00:17:02.861000" , "Josh"       , "???"             ),
        Message(9 , "2019-12-01 00:17:23.229000" , "Mike"       , ":)"              ),
        Message(10, "2019-12-01 00:17:58.811000" , "Jessica"    , "Hi guys!"        ),
        Message(11, "2019-12-01 00:18:59.029000" , "Mike"       , "Shut up!"        )]


def test_token_pop(text_models: list[TextModelInterface], test_messages: list[Message]):
    for model in text_models:
        max_token_threshold: int = model._process_messages(test_messages).tokens
        # print("MAX THRESHOLD: ", max_token_threshold)
        for token_threshold in range(0, max_token_threshold, 20):
            # print("THRESHOLD: ", token_threshold)
            messages_from_oldest: GeneratedConversation = model.conversation_crafter_oldest_to_newest(test_messages, token_threshold)
            messages_from_newest: GeneratedConversation = model.conversation_crafter_newest_to_oldest(test_messages, token_threshold)
            messages_from_center: GeneratedConversation = model.conversation_crafter_center_to_ends  (test_messages, token_threshold)
            # if not model._process_messages(messages_from_oldest.messages).tokens == messages_from_oldest.tokens:
            #     print("OLD", model._process_messages(messages_from_oldest.messages).tokens, messages_from_oldest.tokens, 
            #         messages_from_oldest.tokens - model._process_messages(messages_from_oldest.messages).tokens)
            # if not model._process_messages(messages_from_newest.messages).tokens == messages_from_newest.tokens:
            #     print("NEW", model._process_messages(messages_from_newest.messages).tokens, messages_from_newest.tokens, 
            #           messages_from_newest.tokens - model._process_messages(messages_from_newest.messages).tokens)
            # if not model._process_messages(messages_from_center.messages).tokens == messages_from_center.tokens:
            #     print("CENTER", model._process_messages(messages_from_center.messages).tokens, messages_from_center.tokens,
            #           messages_from_center.tokens - model._process_messages(messages_from_center.messages).tokens)

            assert model._process_messages(messages_from_oldest.messages).tokens <= token_threshold
            assert model._process_messages(messages_from_newest.messages).tokens <= token_threshold
            assert model._process_messages(messages_from_center.messages).tokens <= token_threshold
            # assert model._process_messages(messages_from_oldest.messages).tokens == messages_from_oldest.tokens
            # assert model._process_messages(messages_from_newest.messages).tokens == messages_from_newest.tokens
            # assert model._process_messages(messages_from_center.messages).tokens == messages_from_center.tokens

        # for amount_to_pop in range(pop_testing_range+1):
        #     tokens_removed: int = sum([model.get_tokens_removed_from_subset_pop(0, i, pop_oldest=False) for i in range(amount_to_pop)])
        #     tokens_from_subset: int = model._process_messages(test_messages[:len(test_messages)-amount_to_pop]).tokens
        #     print(amount_to_pop)
        #     assert tokens_from_subset == conversation.tokens - tokens_removed
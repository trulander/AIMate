import logging
from collections import defaultdict
from typing import Sequence, Type
from langchain_core.language_models import LanguageModelLike, BaseChatModel
from langchain_core.messages import SystemMessage, trim_messages, RemoveMessage
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import create_react_agent
from core.config.config import settings
from domain.enums.ai_model import AIModels


logger = logging.getLogger(__name__)


def model_factory(model: AIModels) -> BaseChatModel:
    return ChatGoogleGenerativeAI(model=model.value, api_key=settings.GEMINI_API_KEY)

class LLMAgent:
    def __init__(
        self,
        model: LanguageModelLike,
        tools: Sequence[BaseTool],
        system_message: SystemMessage,
        chat_id: int,
        default_dict_factory: Type[defaultdict,]
    ):
        self._model = model

        # This function will be called every time before the node that calls LLM
        def pre_model_hook(state):
            trimmed_messages = trim_messages(
                state["messages"],
                strategy="last",
                token_counter=count_tokens_approximately,
                max_tokens=200000,
                start_on="human",
                end_on=("human", "tool"),
                include_system=True
            )
            # pprint.pp(trimmed_messages)

            # return {"llm_input_messages": trimmed_messages} #обрезать только для модели, но историю хранить всю
            return {"messages": [RemoveMessage(REMOVE_ALL_MESSAGES)] + trimmed_messages}# обрезать историю в том числе

        # Единый record_id для всех таблиц
        self.checkpointer = InMemorySaver(factory=default_dict_factory)
        logger.info(f"init agent system_message: {system_message}")
        self._agent = create_react_agent(
            # prompt=system_message,
            # pre_model_hook=pre_model_hook,
            model=model,
            tools=tools,
            checkpointer=self.checkpointer
        )

        self._config: RunnableConfig = {
            "configurable": {"thread_id": f"{chat_id}"},
            "recursion_limit": 100,
        }

    def upload_file(self, file):
        print(f"upload file {file} to LLM")
        file_uploaded_id = self._model.upload_file(file).id_  # type: ignore
        return file_uploaded_id

    def invoke(
        self,
        content: list[dict[str, str]],
        attachments: list[str]|None=None,
        temperature: float=0.1
    ) -> str:
        """Отправляет сообщение в чат"""
        message: dict = {
            "role": "user",
            **content
        }
        try:
            logger.info(f"invoke {message}")
            result = self._agent.invoke(
                input = {
                    "messages": [message],
                    "temperature": temperature
                },
                config=self._config
            )
        except GraphRecursionError:

            logger.warning("⚠️ Достигнут лимит reasoning.")
        except Exception as e:
            logger.error(f"InvokeError: {e}")
            raise e
        result = [{i.type: i.content} for i in result.get('messages', [])]
        return result[-2:]


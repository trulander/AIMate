import logging
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import InMemorySaver

from application.interfaces.Irepository_bd_dict import IRepositoryDBDict

from core.ai.ai_agent import model_factory, LLMAgent
from core.ai.db_dict import SQLAlchemyDBDict
from debug_helper import debug_object
from domain.enums.ai_model import AIModels


logger = logging.getLogger(__name__)


class AIService:
    def __init__(
        self,
        repository: IRepositoryDBDict,
        model: AIModels = AIModels.GEMINI_2_0_FLASH,
        chat_id: str | int | None = None,
        system_prompt: str | list[str | dict] = "",
    ):
        logger.info(f"model: {model}")
        self.model = model_factory(model=model)
        self.repository = repository

        system_message = SystemMessage(content=system_prompt)
        default_dict_factory, next_id_record = SQLAlchemyDBDict.db_dict_factory(
            record_id=chat_id, repository=self.repository
        )
        self._agent = LLMAgent(
            default_dict_factory=default_dict_factory,
            system_message=system_message,
            model=self.model,
            tools=[],
            chat_id=next_id_record,
        )

    def get_chat_messages(self):
        debug_object
        result = [f"{i.type}: {i.content}" for i in self._agent.checkpointer.get(config=self._agent._config).get('channel_values',{}).get('messages', [])]
        return result

    def invoke(self,
               human_message: str = "Продолжай",
               ):
        try:
            response = self._agent.invoke(
                content=human_message,
                attachments=None,
                temperature=0.1
            )
            logger.info(f"Последнее сообщение: {response}")
            return response
        finally:
            self._agent.checkpointer.stack.close()
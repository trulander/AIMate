import logging
from langchain_core.messages import SystemMessage
from application.interfaces.Irepository_bd_dict import IRepositoryDBDict
from core.ai.ai_agent import model_factory, LLMAgent
from core.ai.db_dict import SQLAlchemyDBDict
from domain.enums.ai_model import AIModels
from langchain_core.messages import HumanMessage


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
        self.default_dict_factory, self.next_id_record = SQLAlchemyDBDict.db_dict_factory(
            record_id=chat_id, repository=self.repository
        )
        self._agent = LLMAgent(
            default_dict_factory=self.default_dict_factory,
            system_message=system_message,
            model=self.model,
            tools=[],
            chat_id=self.next_id_record,
        )

    def get_current_chat_id(self) -> int:
        return self.next_id_record

    def get_chat_messages(self):
        result = [
            {i.type: i.content}
            for i in self._agent.checkpointer.get(config=self._agent._config)
            .get("channel_values", {})
            .get("messages", [])
        ]
        return result

    def invoke(self,
               human_message: list[dict[str, str]] = None
               ):
        try:
            response = self._agent.invoke(
                content=human_message,
                temperature=0.1
            )
            logger.info(f"Последнее сообщение: {response}")
            return response
        finally:
            self._agent.checkpointer.stack.close()
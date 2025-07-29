from enum import Enum


class AIModels(Enum):
    GEMINI_2_5_FLASH = "gemini-2.5-flash"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"
    GEMINI_2_0_FLASH = "gemini-2.0-flash"
    # GEMINI_2_5_FLASH_PREVIEW_04_17 = "gemini-2.5-flash-preview-04-17"
    GEMINI_2_5_FLASH_LITE_PREVIEW_06_17 = "gemini-2.5-flash-lite-preview-06-17" #Самый худший вариант
    GEMINI_2_0_FLASH_PREVIEW_IMAGE_GENERATION = "gemini-2.0-flash-preview-image-generation"

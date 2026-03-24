import os
import sys
import logging
from dotenv import load_dotenv

# Добавляем корень проекта в пути
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from src.config.qa_config import DEFAULT_KG_MODEL_CONFIG, GraphDBConnectionConfig
from src.kg_model.knowledge_graph_model import KnowledgeGraphModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Загружаем .env для получения путей к базам
    load_dotenv()
    
    logger.info("Инициализация для очистки баз данных...")
    
    # Конфигурация
    kg_model_cfg = DEFAULT_KG_MODEL_CONFIG
    
    # Важно: убеждаемся, что мы НЕ в In-Memory режиме для очистки дисковых баз
    kg_model_cfg.graph_config.driver_config.need_to_clear = False 
    
    try:
        # Инициализируем модель (это откроет соединения)
        kg_model = KnowledgeGraphModel(kg_model_cfg)
        
        logger.info("Очистка KuzuDB (удаление всех узлов и связей, сохранение схемы)...")
        kg_model.graph_struct.db_conn.clear()
        
        logger.info("Очистка ChromaDB (удаление коллекций и пересоздание пустых)...")
        kg_model.vector_struct.nodes_db.clear()
        kg_model.vector_struct.quads_db.clear()
        
        logger.info("✓ Базы данных успешно очищены. Схема сохранена.")
        
    except Exception as e:
        logger.error(f"Ошибка при очистке баз данных: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

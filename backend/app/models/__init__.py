"""All models - import here so SQLAlchemy metadata picks them up."""
from app.models.user import User, Role, Permission, UserRole, RolePermission, Menu, RoleMenu
from app.models.component import ComponentConfig
from app.models.datasource import DataSource
from app.models.datax import DataXTask, DataXFieldMapping
from app.models.spark_task import SparkTask
from app.models.task_instance import TaskInstance
from app.models.data_model import DataModel, DataModelField, DataModelVersion
from app.models.publish import PublishTask, PublishRecord
from app.models.query import SavedQuery, QueryHistory
from app.models.system import SystemConfig, OperationLog
from app.models.data_service import DataServiceApi

__all__ = [
    "User", "Role", "Permission", "UserRole", "RolePermission", "Menu", "RoleMenu",
    "ComponentConfig", "DataSource", "DataXTask", "DataXFieldMapping", "SparkTask",
    "TaskInstance", "DataModel", "DataModelField", "DataModelVersion",
    "PublishTask", "PublishRecord", "SavedQuery", "QueryHistory",
    "SystemConfig", "OperationLog", "DataServiceApi",
]

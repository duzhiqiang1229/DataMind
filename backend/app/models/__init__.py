"""All models - import here so SQLAlchemy metadata picks them up."""
from app.models.user import User, Role, Permission, UserRole, RolePermission, Menu, RoleMenu
from app.models.component import ComponentConfig
from app.models.datasource import DataSource
from app.models.datax import DataXTask, DataXFieldMapping
from app.models.spark_task import SparkTask
from app.models.task_instance import TaskInstance
from app.models.data_model import (
    DataModel, DataModelField, DataModelVersion,
    BusinessDomain, DataDomain,
)
from app.models.publish import PublishTask, PublishRecord
from app.models.query import SavedQuery, QueryHistory
from app.models.system import SystemConfig, OperationLog
from app.models.data_service import DataServiceApi
from app.models.data_service_log import DataServiceCallLog
from app.models.data_service_permission import DataServicePermission
from app.models.metric_category import MetricCategory, MetricMapping, MetricDefinition
from app.models.table_owner import TableOwner
from app.models.datasource_permission import DatasourcePermission
from app.models.dag import DagDefinition, DagNode
from app.models.etl_script import EtlScript
from app.models.airflow_run import AirflowDagRun

__all__ = [
    "User", "Role", "Permission", "UserRole", "RolePermission", "Menu", "RoleMenu",
    "ComponentConfig", "DataSource", "DataXTask", "DataXFieldMapping", "SparkTask",
    "TaskInstance", "DataModel", "DataModelField", "DataModelVersion",
    "BusinessDomain", "DataDomain",
    "PublishTask", "PublishRecord", "SavedQuery", "QueryHistory",
    "SystemConfig", "OperationLog", "DataServiceApi",
    "DataServiceCallLog", "DataServicePermission",
    "MetricCategory", "MetricMapping", "TableOwner", "DatasourcePermission",
    "MetricDefinition",
    "DagDefinition", "DagNode",
    "EtlScript",
    "AirflowDagRun",
]

"""All models - import here so SQLAlchemy metadata picks them up."""
from app.models.user import User, Role, Permission, UserRole, RolePermission, Menu, RoleMenu
from app.models.component import ComponentConfig
from app.models.datasource import DataSource
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
from app.models.data_service_app_key import DataServiceAppKey
from app.models.metric_category import MetricCategory, MetricMapping, MetricDefinition
from app.models.table_owner import TableOwner
from app.models.datasource_permission import DatasourcePermission
from app.models.etl_script import EtlScript
from app.models.airflow_run import AirflowDagRun, AirflowTaskRun
from app.models.data_asset import AssetObject, AssetColumn, AssetLineageEdge, LineageRunEvent, QualityRule, QualityRuleRun
from app.models.mcp import McpClient, McpToken, McpChangeSet, McpChangeSetItem, McpToolCall

__all__ = [
    "User", "Role", "Permission", "UserRole", "RolePermission", "Menu", "RoleMenu",
    "ComponentConfig", "DataSource", "DataModel", "DataModelField", "DataModelVersion",
    "BusinessDomain", "DataDomain",
    "PublishTask", "PublishRecord", "SavedQuery", "QueryHistory",
    "SystemConfig", "OperationLog", "DataServiceApi",
    "DataServiceCallLog", "DataServicePermission", "DataServiceAppKey",
    "MetricCategory", "MetricMapping", "TableOwner", "DatasourcePermission",
    "MetricDefinition",
    "EtlScript",
    "AirflowDagRun", "AirflowTaskRun",
    "AssetObject", "AssetColumn", "AssetLineageEdge", "LineageRunEvent", "QualityRule", "QualityRuleRun",
    "McpClient", "McpToken", "McpChangeSet", "McpChangeSetItem", "McpToolCall",
]

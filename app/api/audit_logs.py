"""审计日志 API"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.tables import AuditLog, AuditLogExport, Agent
from app.core.auth import get_current_agent
from app.core.exceptions import FORBIDDEN, NOT_FOUND
from app.api.dependencies import require_admin
from app.services.audit_export_service import AuditExportService
from app.services.audit_retention_service import AuditRetentionService


# 创建路由
router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


# ============ Pydantic Models ============

class AuditLogFilter(BaseModel):
    """审计日志过滤器"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    action_type: Optional[str] = None
    action_category: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    actor_id: Optional[str] = None
    status: Optional[str] = None
    keyword: Optional[str] = None  # 在目标名称或描述中搜索


class AuditLogResponse(BaseModel):
    """审计日志响应"""
    log_id: str
    actor_id: Optional[str]
    actor_name: Optional[str]
    action_type: str
    action_category: str
    target_type: Optional[str]
    target_id: Optional[str]
    target_name: Optional[str]
    http_method: Optional[str]
    endpoint: Optional[str]
    ip_address: Optional[str]
    status: str
    status_code: Optional[int]
    error_message: Optional[str]
    request_data: Optional[dict]
    response_data: Optional[dict]
    changes: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """审计日志列表响应"""
    total: int
    page: int
    page_size: int
    logs: List[AuditLogResponse]


class AuditLogDetailResponse(AuditLogResponse):
    """审计日志详情响应"""
    user_agent: Optional[str]
    session_id: Optional[str]
    request_id: Optional[str]


class ExportRequest(BaseModel):
    """导出请求"""
    filters: AuditLogFilter
    export_format: str = Field(..., pattern="^(csv|json|pdf)$", description="导出格式: csv, json, pdf")


class ExportResponse(BaseModel):
    """导出任务响应"""
    export_id: str
    status: str
    progress: int
    record_count: int
    created_at: datetime
    completed_at: Optional[datetime]
    file_url: Optional[str]
    expires_at: Optional[datetime]
    error_message: Optional[str]


class ExportListResponse(BaseModel):
    """导出任务列表响应"""
    total: int
    exports: List[ExportResponse]


# ============ 权限验证 ============
# 使用 app.api.dependencies.require_admin


# ============ API 端点 ============

@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    action_type: Optional[str] = Query(None, description="操作类型"),
    action_category: Optional[str] = Query(None, description="操作类别"),
    target_type: Optional[str] = Query(None, description="目标类型"),
    target_id: Optional[str] = Query(None, description="目标ID"),
    actor_id: Optional[str] = Query(None, description="操作者ID"),
    status: Optional[str] = Query(None, description="状态"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    查询审计日志列表

    需要管理员权限。
    """
    # 构建查询条件
    conditions = []

    if start_date:
        conditions.append(AuditLog.created_at >= start_date)
    if end_date:
        conditions.append(AuditLog.created_at <= end_date)
    if action_type:
        conditions.append(AuditLog.action_type == action_type)
    if action_category:
        conditions.append(AuditLog.action_category == action_category)
    if target_type:
        conditions.append(AuditLog.target_type == target_type)
    if target_id:
        conditions.append(AuditLog.target_id == target_id)
    if actor_id:
        conditions.append(AuditLog.actor_agent_id == actor_id)
    if status:
        conditions.append(AuditLog.status == status)
    if keyword:
        conditions.append(
            or_(
                AuditLog.target_name.ilike(f"%{keyword}%"),
                AuditLog.endpoint.ilike(f"%{keyword}%"),
            )
        )

    # 查询总数
    count_query = select(func.count()).select_from(AuditLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # 查询分页数据
    query = select(AuditLog)
    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(desc(AuditLog.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return AuditLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        logs=logs,
    )


@router.get("/{log_id}", response_model=AuditLogDetailResponse)
async def get_audit_log_detail(
    log_id: str,
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    获取审计日志详情

    需要管理员权限。
    """
    result = await db.execute(
        select(AuditLog).where(AuditLog.log_id == log_id)
    )
    log = result.scalar_one_or_none()

    if not log:
        raise NOT_FOUND

    return log


@router.get("/stats/summary")
async def get_audit_stats(
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    获取审计日志统计摘要

    需要管理员权限。
    """
    # 默认最近30天
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()

    # 总日志数
    total_result = await db.execute(
        select(func.count()).select_from(AuditLog).where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        )
    )
    total_logs = total_result.scalar()

    # 按操作类型统计
    by_action_result = await db.execute(
        select(
            AuditLog.action_type,
            func.count().label('count')
        ).where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        ).group_by(AuditLog.action_type)
    )
    by_action = {row.action_type: row.count for row in by_action_result.all()}

    # 按状态统计
    by_status_result = await db.execute(
        select(
            AuditLog.status,
            func.count().label('count')
        ).where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        ).group_by(AuditLog.status)
    )
    by_status = {row.status: row.count for row in by_status_result.all()}

    # 按类别统计
    by_category_result = await db.execute(
        select(
            AuditLog.action_category,
            func.count().label('count')
        ).where(
            and_(
                AuditLog.created_at >= start_date,
                AuditLog.created_at <= end_date
            )
        ).group_by(AuditLog.action_category)
    )
    by_category = {row.action_category: row.count for row in by_category_result.all()}

    return {
        "period": {
            "start_date": start_date,
            "end_date": end_date,
        },
        "total_logs": total_logs,
        "by_action_type": by_action,
        "by_status": by_status,
        "by_category": by_category,
    }


@router.get("/export-types", response_model=List[str])
async def get_export_types(
    current_agent: Agent = Depends(require_admin),
):
    """
    获取支持的导出格式列表

    需要管理员权限。
    """
    return ["csv", "json", "pdf"]


@router.post("/export", response_model=ExportResponse)
async def create_export_task(
    request: ExportRequest,
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    创建审计日志导出任务

    需要管理员权限。
    """
    export_service = AuditExportService()

    # 获取记录数量
    filters_dict = request.filters.model_dump(exclude_none=True)
    record_count = await export_service.count_records(db, **filters_dict)

    # 创建导出任务
    export_record = await export_service.create_export(
        db=db,
        exported_by_id=current_agent.agent_id,
        exported_by_name=current_agent.name,
        export_format=request.export_format,
        filters=filters_dict,
        record_count=record_count,
    )

    # 异步执行导出
    import asyncio
    asyncio.create_task(export_service.perform_export(export_record.export_id))

    return export_record


@router.get("/exports", response_model=ExportListResponse)
async def list_exports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    获取导出任务列表

    需要管理员权限。
    """
    # 查询总数
    count_result = await db.execute(
        select(func.count()).select_from(AuditLogExport)
    )
    total = count_result.scalar()

    # 查询分页数据
    query = select(AuditLogExport)
    query = query.order_by(desc(AuditLogExport.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    exports = result.scalars().all()

    return ExportListResponse(
        total=total,
        exports=exports,
    )


@router.get("/exports/{export_id}", response_model=ExportResponse)
async def get_export_status(
    export_id: str,
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    获取导出任务状态

    需要管理员权限。
    """
    result = await db.execute(
        select(AuditLogExport).where(AuditLogExport.export_id == export_id)
    )
    export = result.scalar_one_or_none()

    if not export:
        raise NOT_FOUND

    return export


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str,
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    下载导出文件

    需要管理员权限。
    """
    result = await db.execute(
        select(AuditLogExport).where(AuditLogExport.export_id == export_id)
    )
    export = result.scalar_one_or_none()

    if not export:
        raise NOT_FOUND

    if export.status != 'completed':
        raise HTTPException(status_code=400, detail="Export not completed")

    if export.expires_at and export.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="Export link expired")

    if not export.file_path:
        raise HTTPException(status_code=400, detail="Export file not found")

    # 返回文件
    filename = f"audit_logs_{export_id[:8]}.{export.export_format}"
    return FileResponse(
        path=export.file_path,
        filename=filename,
        media_type='application/octet-stream',
    )


@router.delete("/exports/{export_id}")
async def delete_export(
    export_id: str,
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    删除导出任务和文件

    需要管理员权限。
    """
    result = await db.execute(
        select(AuditLogExport).where(AuditLogExport.export_id == export_id)
    )
    export = result.scalar_one_or_none()

    if not export:
        raise NOT_FOUND

    # 删除文件
    if export.file_path:
        import os
        try:
            if os.path.exists(export.file_path):
                os.remove(export.file_path)
        except Exception as e:
            print(f"Failed to delete export file: {e}")

    # 删除记录
    await db.delete(export)
    await db.commit()

    return {"message": "Export deleted successfully"}


@router.post("/retention/cleanup")
async def run_retention_cleanup(
    current_agent: Agent = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    手动触发数据保留清理任务

    需要管理员权限。
    """
    retention_service = AuditRetentionService()

    stats = await retention_service.cleanup_expired_logs(db)

    return {
        "message": "Retention cleanup completed",
        "stats": stats,
    }


@router.get("/retention/policy")
async def get_retention_policy(
    current_agent: Agent = Depends(require_admin),
):
    """
    获取数据保留策略

    需要管理员权限。
    """
    return {
        "retention_days": 90,  # 默认保留90天
        "cleanup_interval_days": 7,  # 每7天清理一次
        "archive_enabled": False,  # 是否启用归档
    }

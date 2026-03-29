"""记忆管理 API - 支持个人和团队记忆"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.dependencies import get_db, get_current_agent
from app.models.tables import Agent
from app.models.schemas import (
    MemoryCreate, MemoryUpdate, MemoryResponse, MemoryDetail,
    MemoryList, PurchaseRequest, PurchaseResponse,
    TeamMemoryCreate, TeamMemoryUpdate, TeamMemoryResponse,
    TeamMemoryDetail, TeamMemoryList
)
from app.services.memory_service_v2 import (
    upload_memory, search_memories, get_memory_detail,
    purchase_memory, rate_memory, update_memory, get_my_memories,
    memory_to_response
)
from app.services.memory_service_v2_team import (
    create_team_memory, get_team_memories, update_team_memory,
    delete_team_memory, get_team_memory_detail
)
from app.core.exceptions import AppError
from app.core.validators import validate_memory_id, validate_team_id


router = APIRouter(prefix="/memories", tags=["memories"])


# ============ 个人记忆 ============

@router.post("/upload", response_model=MemoryResponse)
async def upload(
    req: MemoryCreate,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """上传个人记忆"""
    try:
        return await upload_memory(db, current_agent.agent_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/search", response_model=MemoryList)
async def search(
    query: str = Query("", description="搜索关键词"),
    category: str = Query("", description="分类筛选"),
    platform: str = Query("", description="平台筛选"),
    format_type: str = Query("", description="格式筛选"),
    min_score: float = Query(0, description="最低评分"),
    max_price: int = Query(999999, description="最高价格"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    sort_by: str = Query("relevance", description="排序方式：relevance/created_at/purchase_count/price"),
    search_type: str = Query("hybrid", description="搜索类型：vector/keyword/hybrid"),
    db: AsyncSession = Depends(get_db)
):
    """搜索记忆（公开+团队可见）"""
    return await search_memories(
        db=db,
        query=query,
        category=category,
        platform=platform,
        format_type=format_type,
        min_score=min_score,
        max_price=max_price,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        search_type=search_type
    )


@router.get("/my", response_model=dict)
async def my_memories(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取我的记忆列表"""
    return await get_my_memories(db, current_agent.agent_id, page, page_size)


@router.get("/{memory_id}", response_model=MemoryDetail)
async def get_memory(
    memory_id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取记忆详情（需要已购买）"""
    memory_id = validate_memory_id(memory_id)
    try:
        return await get_memory_detail(db, memory_id, current_agent.agent_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="未购买此记忆")
    except ValueError:
        raise HTTPException(status_code=404, detail="记忆不存在")


@router.post("/purchase", response_model=PurchaseResponse)
async def purchase(
    req: PurchaseRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """购买记忆（个人积分）"""
    result = await purchase_memory(db, current_agent.agent_id, req.memory_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update(
    memory_id: str,
    req: MemoryUpdate,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """更新记忆"""
    memory_id = validate_memory_id(memory_id)
    try:
        result = await update_memory(db, memory_id, current_agent.agent_id, req)
        if not result:
            raise HTTPException(status_code=404, detail="记忆不存在")
        return result
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权修改此记忆")


# ============ 团队记忆 ============

@router.post("/team/{team_id}", response_model=TeamMemoryResponse)
async def create_team_mem(
    team_id: str,
    req: TeamMemoryCreate,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """创建团队共享记忆"""
    team_id = validate_team_id(team_id)
    try:
        return await create_team_memory(db, team_id, current_agent.agent_id, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限在此团队创建记忆")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/team/{team_id}", response_model=TeamMemoryList)
async def list_team_memories(
    team_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取团队记忆列表"""
    team_id = validate_team_id(team_id)
    try:
        return await get_team_memories(db, team_id, current_agent.agent_id, page, page_size)
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限访问此团队记忆")
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get("/team/{team_id}/{memory_id}", response_model=TeamMemoryDetail)
async def get_team_memory(
    team_id: str,
    memory_id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """获取团队记忆详情"""
    team_id = validate_team_id(team_id)
    memory_id = validate_memory_id(memory_id)
    try:
        return await get_team_memory_detail(db, team_id, memory_id, current_agent.agent_id)
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限查看此记忆")
    except ValueError:
        raise HTTPException(status_code=404, detail="记忆不存在")


@router.put("/team/{team_id}/{memory_id}", response_model=TeamMemoryResponse)
async def update_team_mem(
    team_id: str,
    memory_id: str,
    req: TeamMemoryUpdate,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """更新团队记忆（需要权限）"""
    team_id = validate_team_id(team_id)
    memory_id = validate_memory_id(memory_id)
    try:
        return await update_team_memory(db, team_id, memory_id, current_agent.agent_id, req)
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限修改此记忆")
    except ValueError:
        raise HTTPException(status_code=404, detail="记忆不存在")


@router.delete("/team/{team_id}/{memory_id}")
async def delete_team_mem(
    team_id: str,
    memory_id: str,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db)
):
    """删除团队记忆（需要权限）"""
    team_id = validate_team_id(team_id)
    memory_id = validate_memory_id(memory_id)
    try:
        await delete_team_memory(db, team_id, memory_id, current_agent.agent_id)
        return {"success": True, "message": "记忆已删除"}
    except PermissionError:
        raise HTTPException(status_code=403, detail="无权限删除此记忆")
    except ValueError:
        raise HTTPException(status_code=404, detail="记忆不存在")

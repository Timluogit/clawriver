"""智能重排 API

- POST /api/reranking/rank          手动重排候选列表
- GET  /api/reranking/config        获取当前重排配置
- PUT  /api/reranking/config        更新重排配置
- POST /api/reranking/evaluate      运行评估
- GET  /api/reranking/stats         获取重排统计
- GET  /api/reranking/strategies    列出可用策略
- POST /api/reranking/ab-test       运行 A/B 测试
- GET  /api/reranking/eval/history  获取评估历史
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.services.smart_reranking import (
    get_smart_reranking_service,
    RerankingConfig,
    RerankingWeights,
    PRESET_STRATEGIES,
)
from app.services.reranking_eval import (
    RerankingEvaluator,
    ABTester,
    get_eval_history,
)

router = APIRouter(prefix="/reranking", tags=["Smart Reranking"])


# ── 请求/响应 Schema ──

class RankRequest(BaseModel):
    query: str
    candidates: List[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]] = None
    top_k: Optional[int] = None
    strategy: Optional[str] = None
    weights_override: Optional[Dict[str, float]] = None


class ConfigUpdateRequest(BaseModel):
    strategy: Optional[str] = None
    weights: Optional[Dict[str, float]] = None
    use_cross_encoder: Optional[bool] = None
    cross_encoder_weight: Optional[float] = None
    enable_dynamic_weights: Optional[bool] = None
    enable_caching: Optional[bool] = None
    cache_ttl: Optional[int] = None
    top_k: Optional[int] = None
    threshold: Optional[float] = None
    min_candidates_for_rerank: Optional[int] = None


class EvalTestCase(BaseModel):
    query: str
    candidates: List[Dict[str, Any]]
    expected_ids: List[str]


class EvalRunRequest(BaseModel):
    test_cases: List[EvalTestCase]
    strategy: Optional[str] = None
    user_profile: Optional[Dict[str, Any]] = None


class ABTestRequest(BaseModel):
    test_cases: List[EvalTestCase]
    strategy_a: str = "balanced"
    strategy_b: str = "semantic_heavy"
    user_profile: Optional[Dict[str, Any]] = None


# ── API 端点 ──

@router.post("/rank", summary="智能重排候选列表")
async def rerank_candidates(req: RankRequest):
    """使用智能重排算法对候选列表进行重排序"""
    service = get_smart_reranking_service()

    results = await service.rerank(
        query=req.query,
        candidates=req.candidates,
        user_profile=req.user_profile,
        top_k=req.top_k,
        strategy=req.strategy,
        override_weights=req.weights_override,
    )

    return {
        "success": True,
        "data": {
            "query": req.query,
            "total_candidates": len(req.candidates),
            "reranked_count": len(results),
            "results": results,
        },
    }


@router.get("/config", summary="获取当前重排配置")
async def get_reranking_config():
    """获取智能重排的当前配置和可用策略列表"""
    service = get_smart_reranking_service()
    config = service.config

    return {
        "success": True,
        "data": {
            "current_config": config.to_dict(),
            "available_strategies": list(PRESET_STRATEGIES.keys()),
            "strategy_descriptions": {
                "balanced": "均衡策略，语义/关键词/质量/时效均匀分配",
                "semantic_heavy": "语义优先，适合复杂语义查询",
                "keyword_heavy": "关键词优先，适合精确匹配场景",
                "freshness_first": "时效优先，适合新闻/动态内容",
                "quality_first": "质量优先，适合高可信度需求",
                "personalized": "个性化优先，适合有用户画像场景",
            },
        },
    }


@router.put("/config", summary="更新重排配置")
async def update_reranking_config(req: ConfigUpdateRequest):
    """动态更新重排配置，无需重启服务"""
    service = get_smart_reranking_service()
    current = service.config

    # 合并更新
    update_dict = {}
    if req.strategy is not None:
        update_dict["strategy"] = req.strategy
    if req.weights is not None:
        update_dict["weights"] = req.weights
    if req.use_cross_encoder is not None:
        update_dict["use_cross_encoder"] = req.use_cross_encoder
    if req.cross_encoder_weight is not None:
        update_dict["cross_encoder_weight"] = req.cross_encoder_weight
    if req.enable_dynamic_weights is not None:
        update_dict["enable_dynamic_weights"] = req.enable_dynamic_weights
    if req.enable_caching is not None:
        update_dict["enable_caching"] = req.enable_caching
    if req.cache_ttl is not None:
        update_dict["cache_ttl"] = req.cache_ttl
    if req.top_k is not None:
        update_dict["top_k"] = req.top_k
    if req.threshold is not None:
        update_dict["threshold"] = req.threshold
    if req.min_candidates_for_rerank is not None:
        update_dict["min_candidates_for_rerank"] = req.min_candidates_for_rerank

    merged = {**current.to_dict(), **update_dict}
    new_config = RerankingConfig.from_dict(merged)
    service.update_config(new_config)

    return {
        "success": True,
        "message": "配置已更新",
        "data": new_config.to_dict(),
    }


@router.post("/evaluate", summary="运行重排评估")
async def run_evaluation(req: EvalRunRequest):
    """使用测试用例运行重排评估，返回 MRR/NDCG/MAP 等指标"""
    service = get_smart_reranking_service()
    evaluator = RerankingEvaluator(service)

    test_cases = [
        {
            "query": tc.query,
            "candidates": tc.candidates,
            "expected_ids": tc.expected_ids,
        }
        for tc in req.test_cases
    ]

    report = await evaluator.evaluate(
        test_cases=test_cases,
        strategy=req.strategy,
        user_profile=req.user_profile,
    )

    # 保存到历史
    history = get_eval_history()
    history.add_report(report)

    return {
        "success": True,
        "data": report.to_dict(),
    }


@router.get("/stats", summary="获取重排统计")
async def get_reranking_stats():
    """获取智能重排服务的运行统计"""
    service = get_smart_reranking_service()
    return {
        "success": True,
        "data": service.get_stats(),
    }


@router.get("/strategies", summary="列出可用策略")
async def list_strategies():
    """列出所有可用的重排策略及其权重配置"""
    strategies = {}
    for name, weights in PRESET_STRATEGIES.items():
        strategies[name] = {
            "weights": weights.to_dict(),
            "description": {
                "balanced": "均衡策略",
                "semantic_heavy": "语义优先",
                "keyword_heavy": "关键词优先",
                "freshness_first": "时效优先",
                "quality_first": "质量优先",
                "personalized": "个性化优先",
            }.get(name, ""),
        }
    return {"success": True, "data": strategies}


@router.post("/ab-test", summary="运行 A/B 测试")
async def run_ab_test(req: ABTestRequest):
    """对比两个重排策略的效果"""
    service = get_smart_reranking_service()
    tester = ABTester(service)

    test_cases = [
        {
            "query": tc.query,
            "candidates": tc.candidates,
            "expected_ids": tc.expected_ids,
        }
        for tc in req.test_cases
    ]

    result = await tester.run_test(
        test_cases=test_cases,
        strategy_a=req.strategy_a,
        strategy_b=req.strategy_b,
        user_profile=req.user_profile,
    )

    history = get_eval_history()
    history.add_ab_test(result)

    return {
        "success": True,
        "data": result.to_dict(),
    }


@router.get("/eval/history", summary="获取评估历史")
async def get_eval_history_list(
    strategy: Optional[str] = Query(None, description="按策略筛选"),
    limit: int = Query(50, ge=1, le=200),
):
    """获取历史评估结果列表"""
    history = get_eval_history()
    return {
        "success": True,
        "data": history.list_reports(strategy=strategy, limit=limit),
    }


@router.get("/eval/compare", summary="对比评估结果")
async def compare_evaluations(
    ids: str = Query(..., description="逗号分隔的评估结果ID"),
):
    """对比多个评估结果"""
    eval_ids = [i.strip() for i in ids.split(",") if i.strip()]
    if len(eval_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个结果ID")

    history = get_eval_history()
    comparison = history.compare_reports(eval_ids)

    if "error" in comparison:
        raise HTTPException(status_code=404, detail=comparison["error"])

    return {"success": True, "data": comparison}

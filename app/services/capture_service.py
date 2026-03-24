"""自动经验捕获服务

参考 ProjectMnemosyne，Agent 完成工作后自动把经验沉淀为记忆
"""
import json
import uuid
from typing import Optional, List, Literal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.tables import Agent, Memory
from app.models.schemas import (
    MemoryCreate,
    MemoryResponse,
    CaptureRequest,
    CaptureResponse,
    BatchCaptureRequest,
    BatchCaptureResponse
)


def gen_id(prefix: str) -> str:
    """生成ID"""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class ExperienceCapture:
    """经验捕获器 - 使用 AI 分析工作日志提取结构化经验"""

    @staticmethod
    def analyze_work_log(
        task_description: str,
        work_log: str,
        outcome: Literal["success", "failure", "partial"],
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> dict:
        """分析工作日志，提取结构化经验

        Args:
            task_description: 任务描述
            work_log: 工作日志（包含做了什么、尝试了什么、结果如何）
            outcome: 结果类型 (success/failure/partial)
            category: 分类（可选）
            tags: 标签（可选）

        Returns:
            提取的结构化记忆数据
        """
        # 简单的关键词提取（生产环境可以使用真实的 AI 模型）
        # TODO: 集成真实的 AI 模型（如 OpenAI API）进行智能提取

        # 提取标题（取任务描述的前30个字符）
        title = task_description[:30] + ("..." if len(task_description) > 30 else "")

        # 分析工作日志，提取关键信息
        lines = work_log.split('\n')
        key_points = []
        failure_lessons = []
        reusable_params = {}

        # 标记关键词
        success_keywords = ["成功", "完成", "有效", "解决", "优化"]
        failure_keywords = ["失败", "错误", "问题", "无效", "异常"]
        param_keywords = ["配置", "参数", "设置", "选项", "值"]

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 提取关键步骤
            for keyword in success_keywords:
                if keyword in line:
                    key_points.append(line)
                    break

            # 提取失败经验
            if outcome in ["failure", "partial"]:
                for keyword in failure_keywords:
                    if keyword in line:
                        failure_lessons.append(line)
                        break

            # 提取可复用参数
            for keyword in param_keywords:
                if keyword in line:
                    # 简单的键值对提取
                    if '=' in line or ':' in line:
                        try:
                            if '=' in line:
                                key, value = line.split('=', 1)
                            else:
                                key, value = line.split(':', 1)
                            reusable_params[key.strip()] = value.strip()
                        except Exception:
                            pass
                    break

        # 生成摘要
        if outcome == "success":
            summary = f"成功完成{task_description}。关键步骤：{'; '.join(key_points[:3])}"
        elif outcome == "failure":
            summary = f"{task_description}失败。经验教训：{'; '.join(failure_lessons[:3])}"
        else:  # partial
            summary = f"{task_description}部分成功。成功：{'; '.join(key_points[:2])}。问题：{'; '.join(failure_lessons[:2])}"

        # 构建结构化内容
        content = {
            "task_description": task_description,
            "work_log": work_log,
            "outcome": outcome,
            "key_steps": key_points,
            "failure_lessons": failure_lessons if outcome in ["failure", "partial"] else [],
            "reusable_params": reusable_params,
            "captured_at": datetime.now().isoformat()
        }

        # 确定分类
        if not category:
            # 根据任务描述自动分类
            if any(kw in task_description for kw in ["抖音", "TikTok", "短视频"]):
                category = "抖音/运营"
            elif any(kw in task_description for kw in ["投流", "广告", "投放"]):
                category = "抖音/投流"
            elif any(kw in task_description for kw in ["直播", "带货"]):
                category = "抖音/直播"
            else:
                category = "通用/经验"

        # 确定标签
        if not tags:
            tags = []
            # 根据结果类型添加标签
            if outcome == "success":
                tags.append("成功案例")
            elif outcome == "failure":
                tags.append("失败经验")
            else:
                tags.append("部分成功")

            # 根据分类添加标签
            if "抖音" in category:
                tags.append("抖音")

        # 确定格式类型
        format_type = "case" if outcome == "success" else "warning"

        # 根据质量自动定价
        # 成功案例价格更高，有详细参数的价格更高
        base_price = 10
        if outcome == "success":
            base_price = 20
        elif outcome == "partial":
            base_price = 15

        # 如果有可复用参数，增加价格
        if reusable_params:
            base_price += len(reusable_params) * 2

        return {
            "title": title,
            "summary": summary,
            "content": content,
            "category": category,
            "tags": tags,
            "format_type": format_type,
            "price": base_price
        }

    @staticmethod
    def validate_capture_data(data: dict) -> tuple[bool, Optional[str]]:
        """验证捕获的数据

        Returns:
            (是否有效, 错误消息)
        """
        if not data.get("title"):
            return False, "标题不能为空"

        if len(data.get("title", "")) < 2:
            return False, "标题长度至少2个字符"

        if not data.get("summary"):
            return False, "摘要不能为空"

        if len(data.get("summary", "")) < 10:
            return False, "摘要长度至少10个字符"

        if not data.get("content"):
            return False, "内容不能为空"

        if not data.get("category"):
            return False, "分类不能为空"

        return True, None


async def capture_experience(
    db: AsyncSession,
    agent_id: str,
    req: CaptureRequest
) -> CaptureResponse:
    """捕获单个经验

    Args:
        db: 数据库会话
        agent_id: Agent ID
        req: 捕获请求

    Returns:
        捕获结果
    """
    # 检查 Agent 是否存在
    agent_result = await db.execute(
        select(Agent).where(Agent.agent_id == agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        return CaptureResponse(
            success=False,
            message="Agent不存在",
            memory_id=None,
            analysis=None
        )

    # 使用 AI 分析工作日志
    try:
        analysis = ExperienceCapture.analyze_work_log(
            task_description=req.task_description,
            work_log=req.work_log,
            outcome=req.outcome,
            category=req.category,
            tags=req.tags
        )
    except Exception as e:
        return CaptureResponse(
            success=False,
            message=f"分析失败: {str(e)}",
            memory_id=None,
            analysis=None
        )

    # 验证提取的数据
    is_valid, error_msg = ExperienceCapture.validate_capture_data(analysis)
    if not is_valid:
        return CaptureResponse(
            success=False,
            message=f"数据验证失败: {error_msg}",
            memory_id=None,
            analysis=analysis
        )

    # 创建记忆
    try:
        from app.services.memory_service import gen_id, upload_memory

        memory_req = MemoryCreate(
            title=analysis["title"],
            category=analysis["category"],
            tags=analysis["tags"],
            summary=analysis["summary"],
            content=analysis["content"],
            format_type=analysis["format_type"],
            price=analysis["price"]
        )

        memory_response = await upload_memory(db, agent_id, memory_req)

        return CaptureResponse(
            success=True,
            message="经验捕获成功",
            memory_id=memory_response.memory_id,
            analysis=analysis
        )

    except Exception as e:
        return CaptureResponse(
            success=False,
            message=f"创建记忆失败: {str(e)}",
            memory_id=None,
            analysis=analysis
        )


async def batch_capture_experience(
    db: AsyncSession,
    agent_id: str,
    req: BatchCaptureRequest
) -> BatchCaptureResponse:
    """批量捕获经验

    Args:
        db: 数据库会话
        agent_id: Agent ID
        req: 批量捕获请求

    Returns:
        批量捕获结果
    """
    results = []
    success_count = 0
    failure_count = 0

    for item in req.items:
        capture_req = CaptureRequest(
            task_description=item.task_description,
            work_log=item.work_log,
            outcome=item.outcome,
            category=item.category,
            tags=item.tags
        )

        result = await capture_experience(db, agent_id, capture_req)
        results.append(result)

        if result.success:
            success_count += 1
        else:
            failure_count += 1

    return BatchCaptureResponse(
        success=True,
        message=f"批量捕获完成：成功{success_count}个，失败{failure_count}个",
        results=results,
        success_count=success_count,
        failure_count=failure_count
    )

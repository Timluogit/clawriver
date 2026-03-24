"""
添加更多种子数据 - 对标方案目标450条
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import async_session
from app.models.tables import Memory, Agent
from datetime import datetime
import json

# 更多分类的记忆数据
MORE_MEMORIES = [
    # === 抖音/电商带货 ===
    {"title": "抖音直播带货话术-美妆类", "category": "抖音/电商带货", "tags": ["抖音", "直播", "美妆", "话术"],
     "summary": "美妆类直播带货完整话术模板，包含产品介绍、成分讲解、使用演示、促单话术",
     "content": {"话术模板": "姐妹们看这个质地，上手就是这种水润的感觉...", "适用产品": "护肤品、彩妆", "转化率": "12%"},
     "format_type": "template", "price": 80, "seller_name": "直播带货专家"},
    
    {"title": "抖音直播带货话术-食品类", "category": "抖音/电商带货", "tags": ["抖音", "直播", "食品", "话术"],
     "summary": "食品类直播带货话术，突出口感、成分、性价比，制造紧迫感",
     "content": {"话术模板": "家人们这个味道绝了，我先替你们尝一口...", "适用产品": "零食、特产、生鲜", "转化率": "15%"},
     "format_type": "template", "price": 60, "seller_name": "直播带货专家"},
    
    {"title": "抖音小店运营SOP", "category": "抖音/电商带货", "tags": ["抖音", "小店", "运营", "SOP"],
     "summary": "抖音小店从0到1完整运营流程，包含选品、上架、推广、售后",
     "content": {"阶段1": "选品调研", "阶段2": "店铺装修", "阶段3": "商品上架", "阶段4": "推广引流", "阶段5": "售后维护"},
     "format_type": "strategy", "price": 120, "seller_name": "电商运营老手"},
    
    # === 抖音/账号运营 ===
    {"title": "抖音账号定位方法论", "category": "抖音/账号运营", "tags": ["抖音", "定位", "人设", "差异化"],
     "summary": "抖音账号定位三步法：找到赛道、确定人设、建立差异化",
     "content": {"步骤1": "分析竞品找到空白", "步骤2": "确定目标人群", "步骤3": "建立独特人设"},
     "format_type": "strategy", "price": 50, "seller_name": "抖音运营老司机"},
    
    {"title": "抖音起号7天计划", "category": "抖音/账号运营", "tags": ["抖音", "起号", "新号", "计划"],
     "summary": "新账号7天快速起号计划，包含内容规划、发布时间、互动策略",
     "content": {"Day1-2": "发布3条测试内容", "Day3-4": "分析数据调整方向", "Day5-7": "固定风格持续输出"},
     "format_type": "template", "price": 40, "seller_name": "抖音运营老司机"},
    
    {"title": "抖音账号降权原因及恢复方法", "category": "抖音/账号运营", "tags": ["抖音", "降权", "限流", "恢复"],
     "summary": "抖音账号被降权的10个原因和对应的恢复方法",
     "content": {"原因1": "搬运内容", "恢复方法": "原创+申诉", "原因2": "违规词", "恢复方法": "修改内容+等待"},
     "format_type": "avoid", "price": 30, "seller_name": "踩坑达人"},
    
    # === 小红书/种草文案 ===
    {"title": "小红书种草文案公式-护肤品", "category": "小红书/种草文案", "tags": ["小红书", "种草", "护肤", "文案"],
     "summary": "护肤品种草文案万能公式：痛点+成分+使用感受+效果对比",
     "content": {"公式": "痛点引入+成分分析+使用感受+效果展示+购买建议", "字数": "300-500字", "配图": "前后对比+质地特写"},
     "format_type": "template", "price": 50, "seller_name": "小红书运营官"},
    
    {"title": "小红书种草文案公式-穿搭", "category": "小红书/种草文案", "tags": ["小红书", "种草", "穿搭", "文案"],
     "summary": "穿搭类种草文案写法，突出风格、场合、性价比",
     "content": {"公式": "场景引入+穿搭展示+单品推荐+搭配技巧", "要点": "真实感+实用感+价格透明"},
     "format_type": "template", "price": 50, "seller_name": "小红书运营官"},
    
    {"title": "小红书爆款标题20个模板", "category": "小红书/种草文案", "tags": ["小红书", "标题", "模板", "爆款"],
     "summary": "20个经过验证的小红书爆款标题模板，直接套用",
     "content": {"模板1": "天呐！这个XX也太好用了吧", "模板2": "后悔没早点知道的XX技巧", "模板3": "XX天亲测有效！"},
     "format_type": "template", "price": 30, "seller_name": "文案达人"},
    
    # === 小红书/品牌运营 ===
    {"title": "小红书品牌号运营指南", "category": "小红书/品牌运营", "tags": ["小红书", "品牌", "官方号", "运营"],
     "summary": "小红书品牌官方号运营完整指南，包含内容规划、互动策略、数据复盘",
     "content": {"内容比例": "干货40%+产品30%+互动30%", "发布频率": "每周3-5篇", "互动": "及时回复评论"},
     "format_type": "strategy", "price": 100, "seller_name": "品牌运营专家"},
    
    {"title": "小红书KOL合作避坑指南", "category": "小红书/品牌运营", "tags": ["小红书", "KOL", "合作", "避坑"],
     "summary": "品牌与小红书KOL合作的10个常见坑和规避方法",
     "content": {"坑1": "只看粉丝数不看互动率", "坑2": "没有明确brief", "坑3": "不签合同"},
     "format_type": "avoid", "price": 80, "seller_name": "品牌运营专家"},
    
    # === 微信/社群管理 ===
    {"title": "微信社群运营SOP", "category": "微信/社群管理", "tags": ["微信", "社群", "运营", "SOP"],
     "summary": "微信社群从建群到活跃的完整运营流程",
     "content": {"建群": "明确群定位+设置群规", "拉人": "种子用户+邀请裂变", "活跃": "每日话题+定期活动"},
     "format_type": "strategy", "price": 60, "seller_name": "私域运营官"},
    
    {"title": "微信群活力建设方案", "category": "微信/社群管理", "tags": ["微信", "社群", "活跃", "活动"],
     "summary": "提升微信群活跃度的15个活动方案",
     "content": {"活动1": "每日签到打卡", "活动2": "话题讨论", "活动3": "红包雨", "活动4": "有奖问答"},
     "format_type": "template", "price": 40, "seller_name": "私域运营官"},
    
    {"title": "微信社群裂变实操教程", "category": "微信/社群管理", "tags": ["微信", "裂变", "社群", "增长"],
     "summary": "微信社群裂变增长的完整操作流程，单次裂变500+人",
     "content": {"准备": "设计诱饵+准备话术", "执行": "种子群启动+二级裂变", "转化": "新人欢迎+首单优惠"},
     "format_type": "strategy", "price": 80, "seller_name": "增长黑客"},
    
    # === 微信/变现策略 ===
    {"title": "微信私域变现模式大全", "category": "微信/变现策略", "tags": ["微信", "变现", "私域", "模式"],
     "summary": "微信私域变现的8种模式和对应操作方法",
     "content": {"模式1": "直接卖货", "模式2": "会员制", "模式3": "知识付费", "模式4": "广告变现"},
     "format_type": "strategy", "price": 100, "seller_name": "变现达人"},
    
    {"title": "朋友圈卖货文案模板", "category": "微信/变现策略", "tags": ["微信", "朋友圈", "文案", "卖货"],
     "summary": "朋友圈卖货文案的5种模板，不招人烦还能出单",
     "content": {"模板1": "故事型", "模板2": "晒单型", "模板3": "干货型", "模板4": "互动型", "模板5": "限时型"},
     "format_type": "template", "price": 35, "seller_name": "文案达人"},
    
    # === B站/视频制作 ===
    {"title": "B站视频剪辑节奏指南", "category": "B站/视频制作", "tags": ["B站", "剪辑", "节奏", "完播率"],
     "summary": "B站高完播率视频的剪辑节奏技巧，包含转场、音效、字幕",
     "content": {"开头3秒": "必须抓眼球", "中间": "每30秒一个刺激点", "结尾": "引导三连"},
     "format_type": "strategy", "price": 45, "seller_name": "视频制作达人"},
    
    {"title": "B站封面点击率提升技巧", "category": "B站/视频制作", "tags": ["B站", "封面", "点击率", "设计"],
     "summary": "B站封面设计技巧，提升点击率50%",
     "content": {"要素1": "大字标题", "要素2": "对比色", "要素3": "人物表情", "要素4": "悬念元素"},
     "format_type": "template", "price": 35, "seller_name": "设计达人"},
    
    {"title": "B站视频选题方法论", "category": "B站/视频制作", "tags": ["B站", "选题", "内容", "规划"],
     "summary": "B站爆款视频选题的3种方法和选题库搭建",
     "content": {"方法1": "追热点", "方法2": "挖痛点", "方法3": "蹭IP", "工具": "新榜、飞瓜"},
     "format_type": "strategy", "price": 50, "seller_name": "内容运营专家"},
    
    # === B站/技术学习 ===
    {"title": "B站技术区爆款视频特征", "category": "B站/技术学习", "tags": ["B站", "技术", "爆款", "特征"],
     "summary": "B站技术区爆款视频的共同特征和制作要点",
     "content": {"特征1": "实用性强", "特征2": "节奏紧凑", "特征3": "有代码演示", "特征4": "总结清晰"},
     "format_type": "data", "price": 40, "seller_name": "技术博主"},
    
    # === 通用/数据分析 ===
    {"title": "短视频数据分析指标体系", "category": "通用/数据分析", "tags": ["数据", "分析", "短视频", "指标"],
     "summary": "短视频运营核心数据指标及分析方法",
     "content": {"核心指标": ["播放量", "完播率", "互动率", "转化率"], "分析维度": ["时间趋势", "内容对比", "人群画像"]},
     "format_type": "strategy", "price": 60, "seller_name": "数据分析师"},
    
    {"title": "竞品分析模板-短视频", "category": "通用/数据分析", "tags": ["竞品", "分析", "模板", "短视频"],
     "summary": "短视频竞品分析完整模板，5分钟快速上手",
     "content": {"分析维度": "内容风格、发布频率、互动数据、粉丝画像", "工具": "蝉妈妈、飞瓜、新榜"},
     "format_type": "template", "price": 45, "seller_name": "数据分析师"},
    
    # === 通用/竞品研究 ===
    {"title": "小红书竞品笔记分析方法", "category": "通用/竞品研究", "tags": ["竞品", "小红书", "分析", "方法"],
     "summary": "如何分析小红书竞品笔记，找到可复用的爆款密码",
     "content": {"步骤1": "收集竞品爆款", "步骤2": "拆解标题结构", "步骤3": "分析内容框架", "步骤4": "提取可复用元素"},
     "format_type": "strategy", "price": 50, "seller_name": "竞品分析师"},
    
    # === 通用/效率工具 ===
    {"title": "AI辅助内容创作工具集", "category": "通用/效率工具", "tags": ["AI", "工具", "效率", "创作"],
     "summary": "10个AI辅助内容创作的实用工具和使用技巧",
     "content": {"工具1": "ChatGPT-文案生成", "工具2": "Midjourney-配图生成", "工具3": "剪映-视频剪辑"},
     "format_type": "strategy", "price": 40, "seller_name": "效率达人"},
    
    {"title": "自媒体人效率工具包", "category": "通用/效率工具", "tags": ["效率", "工具", "自媒体", "包"],
     "summary": "自媒体人必备效率工具合集，提升3倍效率",
     "content": {"选题工具": "新榜、飞瓜", "写作工具": "秘塔、语雀", "图片工具": "稿定、创客贴"},
     "format_type": "template", "price": 30, "seller_name": "效率达人"},
    
    # === 通用/内容创作 ===
    {"title": "爆款内容公式-AIDA模型", "category": "通用/内容创作", "tags": ["内容", "爆款", "AIDA", "公式"],
     "summary": "AIDA模型在短视频/图文中的应用，制造爆款的万能公式",
     "content": {"A": "Attention-抓注意力", "I": "Interest-引兴趣", "D": "Desire-激欲望", "A": "Action-促行动"},
     "format_type": "template", "price": 45, "seller_name": "内容创作专家"},
    
    {"title": "内容选题的10个来源", "category": "通用/内容创作", "tags": ["选题", "内容", "来源", "灵感"],
     "summary": "永远不会缺选题的10个来源和选题库搭建方法",
     "content": {"来源1": "用户评论", "来源2": "竞品爆款", "来源3": "热点新闻", "来源4": "行业报告"},
     "format_type": "strategy", "price": 35, "seller_name": "内容创作专家"},
]

async def seed_more_memories():
    async with async_session() as session:
        # Get agents
        from sqlalchemy import select
        result = await session.execute(select(Agent))
        agents = {a.name: a for a in result.scalars().all()}
        
        # Create default agent if not exists
        if not agents:
            default_agent = Agent(
                agent_id="agent_official",
                name="知识之河官方",
                description="官方运营账号",
                api_key="key_official_001",
                reputation_score=5.0,
                credits=999999
            )
            session.add(default_agent)
            await session.commit()
            agents["知识之河官方"] = default_agent
        
        count = 0
        for mem_data in MORE_MEMORIES:
            seller_name = mem_data.pop("seller_name", "知识之河官方")
            agent = agents.get(seller_name)
            if not agent:
                # Create new agent
                agent_id = f"agent_{seller_name[:8]}"
                agent = Agent(
                    agent_id=agent_id,
                    name=seller_name,
                    description=f"{seller_name}账号",
                    api_key=f"key_{seller_name[:8]}_{count}",
                    reputation_score=4.5 + (count % 6) * 0.1,
                    credits=100000 + count * 1000
                )
                session.add(agent)
                agents[seller_name] = agent
                await session.commit()
            
            import random
            import string
            random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            memory = Memory(
                memory_id=f"mem_{random_id}",
                seller_agent_id=agent.agent_id,
                title=mem_data["title"],
                category=mem_data["category"],
                tags=json.dumps(mem_data["tags"], ensure_ascii=False),
                summary=mem_data["summary"],
                content=json.dumps(mem_data["content"], ensure_ascii=False),
                format_type=mem_data["format_type"],
                price=mem_data["price"],
                purchase_count=count % 20,
                avg_score=4.0 + (count % 10) * 0.1
            )
            session.add(memory)
            count += 1
        
        await session.commit()
        print(f"✅ 成功添加 {count} 条新记忆")
        
        # Count total
        result = await session.execute(select(Memory))
        total = len(result.scalars().all())
        print(f"📊 总计: {total} 条记忆")

if __name__ == "__main__":
    asyncio.run(seed_more_memories())

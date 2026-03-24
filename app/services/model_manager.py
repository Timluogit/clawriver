"""模型管理服务 - 管理嵌入模型和重排模型的下载、加载和缓存

注意：torch / sentence_transformers / transformers 均为懒加载，
仅在实际调用模型时才导入，避免启动时占用大量内存。
"""
from typing import Optional, TYPE_CHECKING
from pathlib import Path
import logging
import hashlib
import json
from datetime import datetime

from app.core.config import settings

if TYPE_CHECKING:
    # 仅用于类型检查，运行时不导入
    from sentence_transformers import CrossEncoder as _CrossEncoder

logger = logging.getLogger(__name__)


class ModelManager:
    """模型管理器

    负责:
    1. 模型下载和缓存
    2. 模型加载（GPU/CPU自动切换）
    3. 模型版本管理
    """

    def __init__(
        self,
        model_cache_dir: Optional[Path] = None,
        force_cpu: bool = False
    ):
        """初始化模型管理器

        Args:
            model_cache_dir: 模型缓存目录
            force_cpu: 强制使用CPU
        """
        # 模型缓存目录
        if model_cache_dir is None:
            model_cache_dir = Path(settings.EMBEDDING_MODEL_DIR) if hasattr(settings, 'EMBEDDING_MODEL_DIR') else Path("models")
        self.model_cache_dir = Path(model_cache_dir)
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)

        # 模型版本信息文件
        self.version_file = self.model_cache_dir / "model_versions.json"

        # 设备选择
        self.force_cpu = force_cpu
        self.device = self._detect_device()
        logger.info(f"ModelManager initialized with device: {self.device}")

        # 模型缓存
        self._cross_encoder: Optional[object] = None
        self._cross_encoder_name: Optional[str] = None

    def _detect_device(self) -> str:
        """检测最佳设备（懒加载 torch）

        Returns:
            'cuda' | 'mps' | 'cpu'
        """
        if self.force_cpu:
            return "cpu"

        try:
            import torch  # 懒加载，仅在调用时导入
            if torch.cuda.is_available():
                cuda_version = torch.version.cuda
                logger.info(f"CUDA available: version {cuda_version}")
                return "cuda"
            if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                logger.info("Apple Silicon MPS available")
                return "mps"
        except ImportError:
            logger.warning("torch not installed, defaulting to cpu")

        logger.info("Using CPU (no GPU/accelerator detected)")
        return "cpu"

    def _load_version_info(self) -> dict:
        """加载模型版本信息"""
        if self.version_file.exists():
            try:
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load version info: {e}")
        return {}

    def _save_version_info(self, versions: dict):
        """保存模型版本信息"""
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump(versions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save version info: {e}")

    def _get_model_path(self, model_name: str) -> Path:
        """获取模型缓存路径

        Args:
            model_name: 模型名称（如 'BAAI/bge-reranker-large'）

        Returns:
            模型缓存目录路径
        """
        # 使用目录名称作为缓存名
        model_hash = hashlib.md5(model_name.encode()).hexdigest()[:8]
        cache_name = f"{model_name.replace('/', '_')}_{model_hash}"
        return self.model_cache_dir / cache_name

    def get_cross_encoder(
        self,
        model_name: str = "BAAI/bge-reranker-large",
        force_reload: bool = False
    ):
        """获取 CrossEncoder 模型（懒加载 sentence_transformers）

        Args:
            model_name: 模型名称
            force_reload: 强制重新加载

        Returns:
            CrossEncoder 实例，如果依赖未安装则返回 None
        """
        if self._cross_encoder is not None and not force_reload and self._cross_encoder_name == model_name:
            return self._cross_encoder

        logger.info(f"Loading CrossEncoder model: {model_name}")

        try:
            from sentence_transformers import CrossEncoder  # 懒加载
            self._cross_encoder = CrossEncoder(
                model_name=model_name,
                device=self.device,
                max_length=512
            )
            self._cross_encoder_name = model_name

            versions = self._load_version_info()
            versions[model_name] = {
                "loaded_at": datetime.now().isoformat(),
                "device": self.device,
                "max_length": 512
            }
            self._save_version_info(versions)

            logger.info(f"CrossEncoder loaded successfully: {model_name} (device: {self.device})")
            return self._cross_encoder

        except ImportError:
            logger.warning(
                "sentence_transformers not installed; CrossEncoder reranking is disabled. "
                "Install with: pip install sentence-transformers"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to load CrossEncoder {model_name}: {e}")
            return None

    def get_model_info(self, model_name: str) -> Optional[dict]:
        """获取模型信息

        Args:
            model_name: 模型名称

        Returns:
            模型信息字典，如果不存在返回 None
        """
        versions = self._load_version_info()
        return versions.get(model_name)

    def clear_cache(self, model_name: Optional[str] = None):
        """清理模型缓存

        Args:
            model_name: 模型名称，如果为 None 则清理所有缓存
        """
        if model_name is None:
            logger.info("Clearing all model cache...")
            # 清空缓存目录
            import shutil
            shutil.rmtree(self.model_cache_dir)
            self.model_cache_dir.mkdir(parents=True, exist_ok=True)
            self.version_file.unlink(missing_ok=True)
        else:
            logger.info(f"Clearing cache for model: {model_name}")
            model_path = self._get_model_path(model_name)
            import shutil
            if model_path.exists():
                shutil.rmtree(model_path)

            # 清除版本信息
            versions = self._load_version_info()
            versions.pop(model_name, None)
            self._save_version_info(versions)

        # 清除内存中的模型
        self._cross_encoder = None
        self._cross_encoder_name = None

        logger.info("Cache cleared")

    def get_cache_size(self) -> dict:
        """获取缓存大小信息

        Returns:
            包含缓存大小统计的字典
        """
        total_size = 0
        model_count = 0

        for path in self.model_cache_dir.rglob("*"):
            if path.is_file():
                total_size += path.stat().st_size

        if self.version_file.exists():
            versions = self._load_version_info()
            model_count = len(versions)

        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "model_count": model_count,
            "cache_dir": str(self.model_cache_dir)
        }


# 全局单例
_model_manager: Optional[ModelManager] = None


def get_model_manager(force_cpu: bool = False) -> ModelManager:
    """获取模型管理器单例

    Args:
        force_cpu: 强制使用CPU

    Returns:
        ModelManager 实例
    """
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager(force_cpu=force_cpu)
    return _model_manager


def reset_model_manager():
    """重置模型管理器（用于测试）"""
    global _model_manager
    _model_manager = None

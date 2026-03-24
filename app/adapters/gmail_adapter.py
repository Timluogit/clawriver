"""
Gmail 适配器
支持邮件列表、下载、解析、附件处理
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import aiohttp
import base64
import email
from email import policy
from email.message import EmailMessage

from ..services.external_source_service import (
    SourceAdapter,
    SourceType,
    File,
    Document,
    DocumentType,
)

logger = logging.getLogger(__name__)


class GmailAdapter(SourceAdapter):
    """Gmail API 适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.access_token = config.get("access_token")
        self.refresh_token = config.get("refresh_token")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.base_url = "https://www.googleapis.com/gmail/v1"
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self) -> bool:
        """初始化适配器"""
        try:
            if not self.access_token:
                raise ValueError("access_token is required")

            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            self._initialized = True
            logger.info("Gmail adapter initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Gmail adapter: {e}")
            return False

    async def connect(self) -> bool:
        """连接到Gmail（验证token）"""
        try:
            await self._get_profile()
            logger.info("Connected to Gmail")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开连接"""
        if self._session:
            await self._session.close()
            self._session = None
        self._initialized = False
        logger.info("Disconnected from Gmail")
        return True

    async def _get_profile(self) -> Dict[str, Any]:
        """获取用户资料"""
        async with self._session.get(f"{self.base_url}/users/me/profile") as resp:
            resp.raise_for_status()
            return await resp.json()

    async def list_files(self, folder_id: Optional[str] = None, limit: int = 100) -> List[File]:
        """Gmail不使用文件列表，返回空"""
        return []

    async def get_file(self, file_id: str) -> Optional[File]:
        """Gmail不使用文件，返回None"""
        return None

    async def download_file(self, file_id: str) -> bytes:
        """Gmail不使用文件下载"""
        raise NotImplementedError("Gmail uses messages, not files")

    async def list_documents(self, limit: int = 100) -> List[Document]:
        """列出邮件文档"""
        try:
            # 获取邮件列表
            params = {
                "maxResults": min(limit, 100),
                "format": "metadata",
                "metadataHeaders": "From,To,Subject,Date",
            }

            async with self._session.get(f"{self.base_url}/users/me/messages", params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

            documents = []
            for message_data in data.get("messages", []):
                message_id = message_data["id"]
                message = await self._get_message(message_id)

                if message:
                    documents.append(message)

            logger.info(f"Listed {len(documents)} emails from Gmail")
            return documents

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise

    async def _get_message(self, message_id: str) -> Optional[Document]:
        """获取邮件详情"""
        try:
            params = {"format": "full"}

            async with self._session.get(
                f"{self.base_url}/users/me/messages/{message_id}",
                params=params
            ) as resp:
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                message_data = await resp.json()

            payload = message_data.get("payload", {})
            headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

            # 解析内容
            subject = headers.get("Subject", "(No Subject)")
            from_addr = headers.get("From", "")
            to_addr = headers.get("To", "")
            date_str = headers.get("Date", "")

            # 提取邮件内容
            body = self._extract_body(payload)

            # 解析附件
            attachments = self._extract_attachments(payload, message_id)

            # 提取作者
            author = from_addr.split("<")[0].strip() if "<" in from_addr else from_addr

            # 解析日期
            created_at = None
            if date_str:
                try:
                    from email.utils import parsedate_to_datetime
                    created_at = parsedate_to_datetime(date_str)
                except Exception:
                    pass

            return Document(
                doc_id=message_id,
                source_type=SourceType.GMAIL,
                title=subject,
                content=body,
                doc_type=DocumentType.EMAIL,
                metadata={
                    "from": from_addr,
                    "to": to_addr,
                    "subject": subject,
                    "date": date_str,
                    "attachments": attachments,
                    "thread_id": message_data.get("threadId"),
                    "label_ids": message_data.get("labelIds", []),
                    "snippet": message_data.get("snippet", ""),
                },
                author=author,
                created_at=created_at or datetime.utcnow(),
                modified_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            return None

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """提取邮件正文"""
        body_parts = []

        def extract_from_part(part: Dict[str, Any]):
            if "body" in part and "data" in part["body"]:
                # Base64解码
                data = part["body"]["data"]
                # Gmail使用URL-safe Base64
                data = data.replace("-", "+").replace("_", "/")
                text = base64.b64decode(data).decode("utf-8", errors="ignore")
                body_parts.append(text)
            elif "parts" in part:
                for subpart in part["parts"]:
                    extract_from_part(subpart)

        extract_from_part(payload)
        return "\n\n".join(body_parts)

    def _extract_attachments(self, payload: Dict[str, Any], message_id: str) -> List[Dict[str, Any]]:
        """提取附件信息"""
        attachments = []

        def extract_from_part(part: Dict[str, Any]):
            if "body" in part and "attachmentId" in part["body"]:
                attachment_id = part["body"]["attachmentId"]
                filename = ""
                mime_type = ""

                for header in part.get("headers", []):
                    if header["name"].lower() == "content-disposition":
                        if "filename=" in header["value"]:
                            filename = header["value"].split("filename=")[1].strip('"')
                    elif header["name"].lower() == "content-type":
                        mime_type = header["value"]

                attachments.append({
                    "id": attachment_id,
                    "filename": filename,
                    "mime_type": mime_type,
                    "size": part["body"].get("size", 0),
                })
            elif "parts" in part:
                for subpart in part["parts"]:
                    extract_from_part(subpart)

        extract_from_part(payload)
        return attachments

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """获取邮件"""
        return await self._get_message(doc_id)

    async def search(self, query: str, limit: int = 10) -> List[Document]:
        """搜索邮件"""
        try:
            params = {
                "q": query,
                "maxResults": min(limit, 100),
                "format": "metadata",
                "metadataHeaders": "From,To,Subject,Date",
            }

            async with self._session.get(
                f"{self.base_url}/users/me/messages",
                params=params
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

            documents = []
            for message_data in data.get("messages", []):
                message_id = message_data["id"]
                message = await self._get_message(message_id)

                if message:
                    documents.append(message)

            return documents

        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            raise

    async def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """下载附件"""
        try:
            async with self._session.get(
                f"{self.base_url}/users/me/messages/{message_id}/attachments/{attachment_id}"
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()

                # Base64解码
                attachment_data = data["data"]
                attachment_data = attachment_data.replace("-", "+").replace("_", "/")
                return base64.b64decode(attachment_data)

        except Exception as e:
            logger.error(f"Failed to download attachment: {e}")
            raise

    async def get_webhook_url(self) -> str:
        """获取Webhook URL（Gmail使用Google Cloud Pub/Sub）"""
        return "https://www.googleapis.com/gmail/v1/users/me/watch"

    async def validate_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """验证Webhook签名（Gmail Pub/Sub使用JWT验证）"""
        return True

    async def handle_webhook(self, payload: Dict[str, Any]) -> List[Document]:
        """处理Webhook事件（Gmail Pub/Sub）"""
        # 实际实现需要处理Pub/Sub推送
        return []

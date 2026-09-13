"""MongoDB Atlas backed persistent memory and conversation history for Nova."""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import List, Dict, Optional

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError


class MemoryManager:
    """Stores Nova's long-term memories and chat history in MongoDB Atlas.

    Configure MONGODB_URI in the environment or pass it through config.json.
    No MongoDB credentials are hard-coded in the project.
    """

    def __init__(self, uri: Optional[str] = None, database: str = "nova", user_id: str = "default"):
        self.uri = (uri or os.environ.get("MONGODB_URI", "")).strip()
        self.database_name = database or "nova"
        self.user_id = user_id or "default"
        self.client = None
        self.db = None
        self.memories = None
        self.conversations = None
        self._lock = threading.RLock()
        self.last_error = ""

        if self.uri:
            self._connect()
        else:
            self.last_error = "MongoDB Atlas URI is not configured."
            print("[MemoryManager] MongoDB Atlas is not configured. Set MONGODB_URI or config.json.")

    @property
    def available(self) -> bool:
        return self.db is not None

    def _connect(self) -> None:
        try:
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                appname="NovaDesktopRobot",
            )
            self.client.admin.command("ping")
            self.db = self.client[self.database_name]
            self.memories = self.db["memories"]
            self.conversations = self.db["conversations"]
            self.memories.create_index([("user_id", ASCENDING), ("importance", DESCENDING), ("updated_at", DESCENDING)])
            self.memories.create_index([("user_id", ASCENDING), ("content", ASCENDING)], unique=True)
            self.conversations.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
            self.last_error = ""
            print(f"[MemoryManager] Connected to MongoDB Atlas database '{self.database_name}'.")
        except Exception as e:
            self.client = self.db = self.memories = self.conversations = None
            self.last_error = str(e)
            print(f"[MemoryManager] MongoDB Atlas connection failed: {e}")

    def reconnect(self, uri: Optional[str] = None, database: Optional[str] = None) -> bool:
        with self._lock:
            if uri is not None:
                self.uri = uri.strip()
            if database:
                self.database_name = database.strip() or "nova"
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass
            self.client = self.db = self.memories = self.conversations = None
            self._connect()
            return self.available

    def status(self) -> str:
        if self.available:
            return f"Connected to MongoDB Atlas ({self.database_name})"
        return f"MongoDB Atlas unavailable: {self.last_error or 'unknown error'}"

    def add(self, content: str, category: str = "general", source: str = "explicit", importance: int = 2) -> bool:
        content = " ".join(content.strip().split())
        if not content or not self.available:
            return False
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": self.user_id,
            "content": content,
            "category": category,
            "source": source,
            "importance": int(importance),
            "created_at": now,
            "updated_at": now,
        }
        try:
            with self._lock:
                self.memories.update_one(
                    {"user_id": self.user_id, "content": content},
                    {"$set": {"category": category, "source": source, "importance": int(importance), "updated_at": now},
                     "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
            return True
        except PyMongoError as e:
            self.last_error = str(e)
            print(f"[MemoryManager] Add memory failed: {e}")
            return False

    def list(self, limit: int = 200) -> List[Dict]:
        if not self.available:
            return []
        try:
            rows = self.memories.find({"user_id": self.user_id}).sort(
                [("importance", DESCENDING), ("updated_at", DESCENDING)]
            ).limit(limit)
            result = []
            for r in rows:
                result.append({
                    "id": str(r["_id"]),
                    "content": r.get("content", ""),
                    "category": r.get("category", "general"),
                    "source": r.get("source", "explicit"),
                    "importance": r.get("importance", 1),
                    "created_at": r.get("created_at").isoformat() if r.get("created_at") else "",
                    "updated_at": r.get("updated_at").isoformat() if r.get("updated_at") else "",
                })
            return result
        except PyMongoError as e:
            self.last_error = str(e)
            return []

    def search(self, query: str, limit: int = 12) -> List[Dict]:
        if not self.available:
            return []
        query = " ".join(query.strip().split())
        try:
            # Atlas Search is optional; this regex-based fallback works with a normal Atlas cluster.
            terms = [t for t in query.split() if len(t) > 2]
            if not terms:
                return self.list(limit)
            pattern = "|".join(__import__("re").escape(t) for t in terms)
            rows = self.memories.find({"user_id": self.user_id, "content": {"$regex": pattern, "$options": "i"}}).sort(
                [("importance", DESCENDING), ("updated_at", DESCENDING)]
            ).limit(limit)
            result = []
            for r in rows:
                result.append({
                    "id": str(r["_id"]),
                    "content": r.get("content", ""),
                    "category": r.get("category", "general"),
                    "source": r.get("source", "explicit"),
                    "importance": r.get("importance", 1),
                    "created_at": r.get("created_at").isoformat() if r.get("created_at") else "",
                    "updated_at": r.get("updated_at").isoformat() if r.get("updated_at") else "",
                })
            return result
        except PyMongoError as e:
            self.last_error = str(e)
            return []

    def delete(self, memory_id: str) -> bool:
        if not self.available:
            return False
        try:
            from bson import ObjectId
            with self._lock:
                result = self.memories.delete_one({"_id": ObjectId(str(memory_id)), "user_id": self.user_id})
            return result.deleted_count > 0
        except Exception:
            return False

    def forget_matching(self, query: str) -> int:
        if not self.available:
            return 0
        query = " ".join(query.strip().split())
        if not query:
            return 0
        try:
            result = self.memories.delete_many({
                "user_id": self.user_id,
                "content": {"$regex": __import__("re").escape(query), "$options": "i"},
            })
            return result.deleted_count
        except PyMongoError as e:
            self.last_error = str(e)
            return 0

    def clear(self) -> int:
        if not self.available:
            return 0
        try:
            result = self.memories.delete_many({"user_id": self.user_id})
            return result.deleted_count
        except PyMongoError as e:
            self.last_error = str(e)
            return 0

    def context_for(self, query: str, limit: int = 8) -> str:
        memories = self.search(query, limit=limit)
        if not memories:
            return "No stored memories are relevant to this request."
        return "\n".join(f"- [{m['category']}] {m['content']}" for m in memories)

    def save_conversation(self, role: str, content: str, session_id: str = "") -> bool:
        if not self.available or not content.strip():
            return False
        try:
            self.conversations.insert_one({
                "user_id": self.user_id,
                "session_id": session_id,
                "role": role,
                "content": content.strip(),
                "created_at": datetime.now(timezone.utc),
            })
            return True
        except PyMongoError as e:
            self.last_error = str(e)
            print(f"[MemoryManager] Conversation save failed: {e}")
            return False

    def recent_conversations(self, limit: int = 12) -> List[Dict]:
        if not self.available:
            return []
        try:
            rows = list(self.conversations.find({"user_id": self.user_id}).sort("created_at", DESCENDING).limit(limit))
            rows.reverse()
            return [{"role": r.get("role", "user"), "content": r.get("content", "")} for r in rows]
        except PyMongoError as e:
            self.last_error = str(e)
            return []

    def clear_conversations(self) -> int:
        if not self.available:
            return 0
        try:
            result = self.conversations.delete_many({"user_id": self.user_id})
            return result.deleted_count
        except PyMongoError as e:
            self.last_error = str(e)
            return 0

    def close(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass

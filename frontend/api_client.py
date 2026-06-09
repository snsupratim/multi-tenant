import os
import requests
from typing import Optional
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BASE_URL = st.secrets.get(
    "BACKEND_URL",
    os.getenv("BACKEND_URL")
)

if not BASE_URL:
    raise ValueError("BACKEND_URL is not configured")

class APIClient:
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token
        self.session = requests.Session()

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.access_token:
            h["Authorization"] = f"Bearer {self.access_token}"
        return h

    # ── Auth ──────────────────────────────────────────────────────────────────

    def register(self, email: str, username: str, password: str) -> dict:
        r = self.session.post(
            f"{BASE_URL}/auth/register",
            json={"email": email, "username": username, "password": password},
        )
        return r.json(), r.status_code

    def login(self, username: str, password: str) -> dict:
        r = self.session.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "password": password},
        )
        return r.json(), r.status_code

    def me(self) -> dict:
        r = self.session.get(f"{BASE_URL}/auth/me", headers=self._headers())
        return r.json(), r.status_code

    # ── Documents ─────────────────────────────────────────────────────────────

    def upload_document(self, file_bytes: bytes, filename: str) -> dict:
        r = self.session.post(
            f"{BASE_URL}/documents/upload",
            files={"file": (filename, file_bytes)},
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        return r.json(), r.status_code

    def list_documents(self) -> dict:
        r = self.session.get(f"{BASE_URL}/documents/", headers=self._headers())
        return r.json(), r.status_code

    def delete_document(self, doc_id: str) -> int:
        r = self.session.delete(
            f"{BASE_URL}/documents/{doc_id}", headers=self._headers()
        )
        return r.status_code

    def get_document(self, doc_id: str) -> dict:
        r = self.session.get(
            f"{BASE_URL}/documents/{doc_id}", headers=self._headers()
        )
        return r.json(), r.status_code

    # ── Query ─────────────────────────────────────────────────────────────────

    def query(self, question: str, top_k: int = 5, temperature: float = 0.3) -> dict:
        r = self.session.post(
            f"{BASE_URL}/query/",
            json={"query": question, "top_k": top_k, "temperature": temperature},
            headers=self._headers(),
        )
        return r.json(), r.status_code

    def query_history(self, limit: int = 20) -> dict:
        r = self.session.get(
            f"{BASE_URL}/query/history?limit={limit}", headers=self._headers()
        )
        return r.json(), r.status_code

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        r = self.session.get(f"{BASE_URL}/stats/", headers=self._headers())
        return r.json(), r.status_code

    def get_namespace_stats(self) -> dict:
        r = self.session.get(
            f"{BASE_URL}/stats/namespace", headers=self._headers()
        )
        return r.json(), r.status_code

#!/usr/bin/env python3
"""
Cliente standalone da API Beeno para a skill beeno-crm-readonly-notes.

Escopo restrito por design:
- Todas as 21 operacoes de leitura do modo BEENO_READONLY do MCP
- Uma unica operacao de escrita: criar nota em deal (POST /notes/deal/{dealId})

Operacoes fora desse escopo (criar/atualizar/deletar entidades, notas em contatos,
associations, automation, WhatsApp) NAO sao implementadas — sao bloqueadas por design.

Variaveis de ambiente:
- BEENO_DOMAIN (obrigatorio) — ex: https://acme.beeno.com.br
- BEENO_API_KEY (obrigatorio)
- BEENO_API_KEY_NAME (opcional, default: ELOZ-APIKEY) — nome do header de auth
"""

import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Dict, List, Literal, Optional

from utils import (
    ApiError,
    ScopeError,
    load_env_file,
    require_env_var,
    get_env_var,
)


REQUEST_TIMEOUT_SEC = 30
MAX_PAGES = 500
DEFAULT_LIMIT = 100

NoteType = Literal["general", "email", "call", "meeting", "whatsapp"]
SortField = Literal["date_modified", "date_added", "createdAt", "updatedAt"]
SortOrder = Literal["asc", "desc"]
FilterOperator = Literal[
    "EQ", "NEQ", "GT", "LT", "GTE", "LTE",
    "IN", "NOT_IN", "HAS_PROPERTY", "NOT_HAS_PROPERTY",
    "CONTAINS_TOKEN", "NOT_CONTAINS_TOKEN",
]


class BeenoClient:
    """Cliente HTTP minimo para a API Beeno, restrito ao escopo da skill."""

    def __init__(
        self,
        domain: Optional[str] = None,
        api_key: Optional[str] = None,
        api_key_name: Optional[str] = None,
        auto_load_env: bool = True,
    ):
        if auto_load_env:
            load_env_file(".env")

        self.domain = (domain or require_env_var("BEENO_DOMAIN")).rstrip("/")
        self.api_key = api_key or require_env_var("BEENO_API_KEY")
        self.api_key_name = (
            api_key_name
            or get_env_var("BEENO_API_KEY_NAME", "ELOZ-APIKEY")
        )
        self.base_url = f"{self.domain}/api/v1"

    # ─────────────────────────── HTTP plumbing ──────────────────────────── #

    def _headers(self) -> Dict[str, str]:
        return {
            self.api_key_name: self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _build_url(self, path: str, params: Optional[Dict[str, Any]] = None) -> str:
        url = f"{self.base_url}{path}"
        if not params:
            return url
        clean = {k: str(v) for k, v in params.items() if v is not None and v != ""}
        if not clean:
            return url
        return f"{url}?{urllib.parse.urlencode(clean)}"

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = self._build_url(path, params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SEC) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
            try:
                err_body = json.loads(raw)
                msg = err_body.get("message") or err_body.get("error") or raw
            except json.JSONDecodeError:
                msg = raw or f"HTTP {e.code}"
            raise ApiError(e.code, msg, f"{method} {path}") from e

        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self._request("POST", path, params=params, body=body)

    def _post_all_pages(
        self,
        path: str,
        body: Dict[str, Any],
        max_results: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Pagina automaticamente um endpoint POST /search."""
        all_results: List[Any] = []
        seen: set = set()
        cursor: Optional[str] = None
        prev_cursor: Optional[str] = None
        total = 0
        pages = 0
        stale_pages = 0
        MAX_STALE = 2

        while True:
            params: Dict[str, Any] = {"limit": DEFAULT_LIMIT}
            if cursor:
                params["cursor"] = cursor
            data = self._post(path, body=body, params=params)
            total = data.get("total") or total
            results = data.get("results") or []
            if not results:
                break

            new_items = 0
            for item in results:
                _id = item.get("id")
                if _id is not None and _id in seen:
                    continue
                if _id is not None:
                    seen.add(_id)
                all_results.append(item)
                new_items += 1
            pages += 1

            if new_items == 0:
                stale_pages += 1
                if stale_pages >= MAX_STALE:
                    break
            else:
                stale_pages = 0

            if pages >= MAX_PAGES:
                break
            if max_results and len(all_results) >= max_results:
                break
            if total and len(all_results) >= total:
                break

            next_cursor = (data.get("cursor") or {}).get("next")
            if next_cursor and next_cursor == prev_cursor:
                break
            prev_cursor = cursor
            cursor = next_cursor
            if not cursor:
                break

        if max_results:
            all_results = all_results[:max_results]
        truncated = bool(total and len(all_results) < total)
        out: Dict[str, Any] = {
            "total": total,
            "results": all_results,
            "fetched": len(all_results),
            "truncated": truncated,
        }
        if truncated:
            out["message"] = (
                f"Results limited to {len(all_results)} of {total}. "
                "Use max_results to increase or paginate manually."
            )
        return out

    # ───────────────────────────── Contacts ─────────────────────────────── #

    def contacts_list(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        campaign_id: Optional[str] = None,
        segment_id: Optional[str] = None,
        properties: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
        include_associations: Optional[bool] = None,
    ) -> Any:
        params = {
            "limit": limit, "cursor": cursor,
            "campaignId": campaign_id, "segmentId": segment_id,
            "properties": properties, "sort": sort, "order": order,
            "includeAssociations": (
                str(include_associations).lower() if include_associations is not None else None
            ),
        }
        return self._get("/contacts", params=params)

    def contacts_read(self, contact_id: str) -> Any:
        return self._get(f"/contacts/{contact_id}")

    def contacts_search(
        self,
        filters: List[Dict[str, Any]],
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
        fetch_all: bool = False,
        max_results: Optional[int] = None,
    ) -> Any:
        body: Dict[str, Any] = {"filters": filters}
        if properties is not None:
            body["properties"] = properties
        if sort is not None:
            body["sort"] = sort
        if order is not None:
            body["order"] = order
        if fetch_all:
            return self._post_all_pages("/contacts/search", body, max_results=max_results)
        return self._post("/contacts/search", body=body, params={"limit": limit, "cursor": cursor})

    # ────────────────────────────── Deals ───────────────────────────────── #

    def deals_list(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
        properties: Optional[str] = None,
        include_associations: Optional[bool] = None,
    ) -> Any:
        params = {
            "limit": limit, "cursor": cursor, "sort": sort, "order": order,
            "properties": properties,
            "includeAssociations": (
                str(include_associations).lower() if include_associations is not None else None
            ),
        }
        return self._get("/deals", params=params)

    def deals_read(self, deal_id: str) -> Any:
        return self._get(f"/deals/{deal_id}")

    def deals_search(
        self,
        filters: List[Dict[str, Any]],
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
        fetch_all: bool = False,
        max_results: Optional[int] = None,
    ) -> Any:
        body: Dict[str, Any] = {"filters": filters}
        if properties is not None:
            body["properties"] = properties
        if sort is not None:
            body["sort"] = sort
        if order is not None:
            body["order"] = order
        if fetch_all:
            return self._post_all_pages("/deals/search", body, max_results=max_results)
        return self._post("/deals/search", body=body, params={"limit": limit, "cursor": cursor})

    # ──────────────────────────── Companies ─────────────────────────────── #

    def companies_list(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
        properties: Optional[str] = None,
        include_associations: Optional[bool] = None,
    ) -> Any:
        params = {
            "limit": limit, "cursor": cursor, "sort": sort, "order": order,
            "properties": properties,
            "includeAssociations": (
                str(include_associations).lower() if include_associations is not None else None
            ),
        }
        return self._get("/companies", params=params)

    def companies_read(self, company_id: str) -> Any:
        return self._get(f"/companies/{company_id}")

    def companies_search(
        self,
        filters: List[Dict[str, Any]],
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
        fetch_all: bool = False,
        max_results: Optional[int] = None,
    ) -> Any:
        body: Dict[str, Any] = {"filters": filters}
        if properties is not None:
            body["properties"] = properties
        if sort is not None:
            body["sort"] = sort
        if order is not None:
            body["order"] = order
        if fetch_all:
            return self._post_all_pages("/companies/search", body, max_results=max_results)
        return self._post("/companies/search", body=body, params={"limit": limit, "cursor": cursor})

    # ───────────────────────────── Products ─────────────────────────────── #

    def products_list(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
    ) -> Any:
        return self._get("/products", params={
            "limit": limit, "cursor": cursor, "sort": sort, "order": order,
        })

    def products_read(self, product_id: str) -> Any:
        return self._get(f"/products/{product_id}")

    def products_search(
        self,
        filters: List[Dict[str, Any]],
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
        fetch_all: bool = False,
        max_results: Optional[int] = None,
    ) -> Any:
        body: Dict[str, Any] = {"filters": filters}
        if sort is not None:
            body["sort"] = sort
        if order is not None:
            body["order"] = order
        if fetch_all:
            return self._post_all_pages("/products/search", body, max_results=max_results)
        return self._post("/products/search", body=body, params={"limit": limit, "cursor": cursor})

    # ────────────────────────────── Tasks ───────────────────────────────── #

    def tasks_list(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
    ) -> Any:
        return self._get("/tasks", params={
            "limit": limit, "cursor": cursor, "sort": sort, "order": order,
        })

    def tasks_read(self, task_id: str) -> Any:
        return self._get(f"/tasks/{task_id}")

    def tasks_search(
        self,
        filters: List[Dict[str, Any]],
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[SortField] = None,
        order: Optional[SortOrder] = None,
        fetch_all: bool = False,
        max_results: Optional[int] = None,
    ) -> Any:
        body: Dict[str, Any] = {"filters": filters}
        if sort is not None:
            body["sort"] = sort
        if order is not None:
            body["order"] = order
        if fetch_all:
            return self._post_all_pages("/tasks/search", body, max_results=max_results)
        return self._post("/tasks/search", body=body, params={"limit": limit, "cursor": cursor})

    # ────────────────────────────── Forms ───────────────────────────────── #

    def forms_list(self, limit: Optional[int] = None, cursor: Optional[str] = None) -> Any:
        return self._get("/forms", params={"limit": limit, "cursor": cursor})

    def forms_read(self, form_id: str) -> Any:
        return self._get(f"/forms/{form_id}")

    # ──────────────────────────── Pipelines ─────────────────────────────── #

    def pipelines_list(self) -> Any:
        return self._get("/deals/pipelines")

    # ────────────────────────────── Notes ───────────────────────────────── #

    def notes_list(
        self,
        from_object: Literal["deal", "contact"],
        from_object_id: str,
    ) -> Any:
        if from_object not in ("deal", "contact"):
            raise ScopeError(f"from_object deve ser 'deal' ou 'contact', recebido: {from_object!r}")
        return self._get(f"/notes/{from_object}/{from_object_id}")

    def create_deal_note(
        self,
        deal_id: str,
        text: str,
        note_type: NoteType = "general",
        files: Optional[List[Dict[str, str]]] = None,
    ) -> Any:
        """Cria uma nota em um deal. UNICA operacao de escrita permitida pela skill.

        Notas em contatos NAO sao suportadas por design (escopo da skill).
        """
        if note_type not in ("general", "email", "call", "meeting", "whatsapp"):
            raise ScopeError(
                f"note_type invalido: {note_type!r}. "
                "Valores aceitos: general, email, call, meeting, whatsapp."
            )
        if not deal_id or not str(deal_id).strip():
            raise ScopeError("deal_id obrigatorio para criar nota em deal.")
        if not text or not text.strip():
            raise ScopeError("text obrigatorio para criar nota.")

        properties: Dict[str, Any] = {"text": text, "type": note_type}
        if files is not None:
            properties["files"] = files
        return self._post(f"/notes/deal/{deal_id}", body={"properties": properties})

    # ──────────────────────────── Properties ────────────────────────────── #

    def properties_list(
        self,
        object_type: Literal["deal", "contact", "company"],
        filter_text: Optional[str] = None,
        include_options: bool = False,
    ) -> List[Dict[str, Any]]:
        """Lista propriedades de um tipo de objeto, ja resumidas (alias/label/type/group)."""
        if object_type not in ("deal", "contact", "company"):
            raise ScopeError(f"object_type invalido: {object_type!r}")
        result = self._get(f"/properties/{object_type}")
        if isinstance(result, list):
            properties = result
        elif isinstance(result, dict):
            properties = result.get("results") or result.get("properties") or [result]
        else:
            properties = []

        summarized: List[Dict[str, Any]] = []
        for prop in properties:
            summary: Dict[str, Any] = {
                "alias": prop.get("alias"),
                "label": prop.get("label"),
                "type": prop.get("type"),
                "group": prop.get("group"),
            }
            if prop.get("type") in ("select", "multiselect"):
                opts = (prop.get("properties") or {}).get("list") or prop.get("options") or []
                summary["optionsCount"] = len(opts)
                if include_options:
                    summary["options"] = opts
            summarized.append(summary)

        if filter_text:
            ft = filter_text.lower()
            summarized = [
                p for p in summarized
                if (p.get("alias") and ft in p["alias"].lower())
                or (p.get("label") and ft in p["label"].lower())
            ]
        return summarized

    # ───────────────────────────── Segments ─────────────────────────────── #

    def segments_list(
        self,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        sort: Optional[str] = None,
        order: Optional[SortOrder] = None,
    ) -> Any:
        return self._get("/segments", params={
            "limit": limit, "cursor": cursor, "sort": sort, "order": order,
        })


# ─────────────────────── Helpers para uso interativo ───────────────────── #

def make_filter(
    property_name: str,
    operator: FilterOperator,
    value: Optional[str] = None,
    values: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Cria um objeto de filtro para usar em *_search().

    Use `value` para operadores single-value (EQ, NEQ, GT, LT, etc.)
    Use `values` para operadores de lista (IN, NOT_IN).
    """
    f: Dict[str, Any] = {"propertyName": property_name, "operator": operator}
    if values is not None:
        f["values"] = values
    if value is not None:
        f["value"] = value
    return f

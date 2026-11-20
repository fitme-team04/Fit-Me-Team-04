"""The V2 worker stores shareable garments in a separate MySQL schema."""
import base64
import binascii
import json
from typing import Annotated, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from listing_fit import Category, Cm, Label, Source
from team_bridge import _db

OpaqueID = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]


class CatalogSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    garment_id: int = Field(gt=0, le=2_147_483_647)
    size_id: int = Field(gt=0, le=2_147_483_647)


class Outline(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    w: int = Field(ge=3, le=120)
    h: int = Field(ge=3, le=120)
    rgb: list[Annotated[int, Field(ge=0, le=255)]] = Field(min_length=3, max_length=3)
    bits: str = Field(max_length=2400)

    @model_validator(mode="after")
    def check_mask(self):
        try:
            actual = base64.b64decode(self.bits, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Invalid outline") from exc
        if len(actual) != (self.w * self.h + 7) // 8:
            raise ValueError("Invalid outline size")
        return self


class Listing(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: Literal[1]
    name: str = Field(min_length=1, max_length=160, pattern=r"\S")
    category: Category
    size: str = Field(max_length=60)
    note: str = Field(max_length=240)
    rows: list[tuple[Label, Cm, Source]] = Field(min_length=1, max_length=32)
    model: Outline | None = None
    projection: tuple[Cm, Cm] | None = None
    modelAsset: OpaqueID | None = None
    catalogSelection: CatalogSelection | None = None
    example: bool = False
    demoId: Literal["brick-tee"] | None = None

    @model_validator(mode="after")
    def check_rows(self):
        if len({row[0] for row in self.rows}) != len(self.rows):
            raise ValueError("Duplicate dimensions")
        if self.projection and not self.model:
            raise ValueError("Projection needs an outline")
        if self.demoId and not self.example:
            raise ValueError("An example garment must be labeled")
        return self


def initialize():
    with _db.connect() as conn, conn.cursor() as cur:
        cur.execute("CREATE DATABASE IF NOT EXISTS fitme_v2 CHARACTER SET utf8mb4")
        cur.execute("""CREATE TABLE IF NOT EXISTS fitme_v2.captures (
            id CHAR(32) PRIMARY KEY, result_json JSON NOT NULL, blob_name VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS fitme_v2.listings (
            id CHAR(32) PRIMARY KEY, card_json JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        conn.commit()


def save_listing(key, card):
    data = json.dumps(card, ensure_ascii=False)
    with _db.connect() as conn, conn.cursor() as cur:
        if card.get("modelAsset"):
            cur.execute("SELECT id FROM fitme_v2.captures WHERE id=%s AND blob_name IS NOT NULL",
                        (card["modelAsset"],))
            if not cur.fetchone():
                raise HTTPException(422, "연결할 3D 모델을 찾을 수 없어요.")
        cur.execute("INSERT INTO fitme_v2.listings (id, card_json) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id=id",
                    (key, data))
        cur.execute("SELECT card_json FROM fitme_v2.listings WHERE id=%s", (key,))
        if json.loads(cur.fetchone()["card_json"]) != card:
            raise HTTPException(409, "수정한 매물은 새 링크로 공유해 주세요.")
        conn.commit()
    return {"id": key}


def get_listing(key):
    rows = _db.query("SELECT card_json FROM fitme_v2.listings WHERE id=%s", (key,))
    if not rows:
        raise HTTPException(404, "이 매물을 찾을 수 없어요. 판매자에게 링크를 확인해 주세요.")
    return json.loads(rows[0]["card_json"])


def listing_replay(key, card):
    rows = _db.query("SELECT card_json FROM fitme_v2.listings WHERE id=%s", (key,))
    if not rows:
        return {}
    if json.loads(rows[0]["card_json"]) != card:
        raise HTTPException(409, "수정한 매물은 새 링크로 공유해 주세요.")
    return {"id": key}


def save_capture(key, result, blob_name):
    with _db.connect() as conn, conn.cursor() as cur:
        cur.execute("""INSERT INTO fitme_v2.captures (id,result_json,blob_name) VALUES (%s,%s,%s)
                       ON DUPLICATE KEY UPDATE id=id""",
                    (key, json.dumps(result, ensure_ascii=False), blob_name))
        conn.commit()


def capture(key):
    rows = _db.query("SELECT result_json,blob_name FROM fitme_v2.captures WHERE id=%s", (key,))
    return rows[0] if rows else None


if __name__ == "__main__":
    initialize()

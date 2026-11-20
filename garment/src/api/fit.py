# 역할: 상품의 모든 국내 사이즈 실측과 신체 둘레를 읽어 여유분 판정 결과를 반환합니다.
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from database.connection import query
from database import brand_catalog
from storage.blob_assets import principal
from ease_check import MEASURES_SQL, sizes_from_db_rows, check_all_sizes, DEFAULT_REGION

router = APIRouter()


class FitRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    item_code: str = Field(min_length=1, max_length=64, strict=True)
    size_label: str = Field(min_length=1, max_length=64, strict=True)
    chest_girth_cm: float | None = Field(default=None, strict=True)
    waist_girth_cm: float | None = Field(default=None, strict=True)
    hip_girth_cm: float | None = Field(default=None, strict=True)

    @field_validator('item_code', 'size_label')
    @classmethod
    def strip_required(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('A nonblank item_code and size_label are required')
        return value


@router.post('/fit')
def fit(choice: FitRequest, subject: str = Depends(principal)):
    rows = query(MEASURES_SQL, (choice.item_code,))
    sizes = sizes_from_db_rows(rows)
    # Include sizes with no measure rows so missing data yields UNDETERMINED, never an invented FIT.
    catalog = query('''SELECT g.category, s.size_label, s.region
        FROM garment.garments g LEFT JOIN garment.sizes s ON s.garment_id=g.garment_id
        WHERE g.item_code=? ORDER BY s.size_id''', (choice.item_code,))
    if not catalog:
        try:
            _,brand_rows = brand_catalog.product(choice.item_code,only_bottoms=True)
            if not brand_rows:
                raise HTTPException(404,'Unknown item_code')
            sizes = sizes_from_db_rows(brand_catalog.measure_rows(brand_rows))
            categories = {row['category'] for row in brand_rows}
            if len(categories)!=1:
                raise ValueError('Brand product category is ambiguous')
            body = choice.model_dump(include={'chest_girth_cm','waist_girth_cm','hip_girth_cm'})
            return check_all_sizes(categories.pop(),body,sizes,choice.size_label)
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from exc
    known = {size['size_label'] for size in sizes}
    for row in catalog:
        label = row['size_label']
        if label is not None and row['region'] in (None, DEFAULT_REGION) and label not in known:
            sizes.append({'size_label': label})
            known.add(label)
    if choice.size_label not in known:
        raise HTTPException(422, 'Selected size_label is not registered for this product in KR')
    categories = {row['category'] for row in catalog}
    if len(categories) != 1:
        raise HTTPException(422, 'Product category is ambiguous')
    body = choice.model_dump(include={'chest_girth_cm', 'waist_girth_cm', 'hip_girth_cm'})
    try:
        return check_all_sizes(categories.pop(), body, sizes, choice.size_label)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

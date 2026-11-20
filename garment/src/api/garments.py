# 역할: 실상품·사이즈 조회와 선택 의류의 GLB 생성 API를 제공합니다.
"""Select catalog templates for SAM fitting or render standalone catalog sizes."""
import math
import pyodbc
from core.garment_specs import validate_spec, LIMITS
from core.catalog_mapping import category_template, generation_settings
from geometry.template_catalog import resolve_template
from database import brand_catalog
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from core.runtime import render
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool
from storage.model_cache import ensure_models

ROOT = Path(__file__).resolve().parent
@asynccontextmanager
async def lifespan(app):
    await run_in_threadpool(ensure_models)
    yield

app = FastAPI(title="FitMe Garments",lifespan=lifespan)
from api.fit import router as fit_router
app.include_router(fit_router)
class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_code: str | None = Field(default=None, min_length=1, max_length=64, strict=True)
    garment_id: int | None = Field(default=None, gt=0, strict=True)
    size_id: int | None = Field(default=None, gt=0, strict=True)
    size_label: str | None = Field(default=None, min_length=1, max_length=64, strict=True)
    body_model_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def product_required(self):
        if self.item_code is None and self.garment_id is None:
            raise ValueError('Provide item_code or garment_id')
        if self.item_code is not None and not self.item_code.strip():
            raise ValueError('item_code cannot be blank')
        if self.size_id is None and self.size_label is None:
            raise ValueError('Provide size_id or size_label')
        if self.size_label is not None and not self.size_label.strip():
            raise ValueError('size_label cannot be blank')
        if self.size_id is None and self.item_code is None:
            raise ValueError('Selecting by size_label requires item_code')
        return self

from database.connection import query, DatabaseUnavailable
from storage.blob_assets import downloads, principal
from fastapi import Depends


@app.exception_handler(DatabaseUnavailable)
@app.exception_handler(pyodbc.OperationalError)
async def database_unavailable(request, error):
    return JSONResponse(status_code=503,headers={'Retry-After':'5'},content={
        'detail':'의류 데이터베이스에 연결할 수 없어요. 잠시 뒤 다시 시도해 주세요.'})

@app.get("/api/garments")
def catalog():
    return query("SELECT garment_id,item_code,garment_name,category FROM garment.garments ORDER BY garment_id")


@app.get('/api/garments/by-item/{item_code}/sizes')
def sizes_by_item(item_code: str):
    rows = query('''SELECT s.size_id,s.garment_id,s.size_label,s.region
        FROM garment.garments g JOIN garment.sizes s ON s.garment_id=g.garment_id
        WHERE g.item_code=? ORDER BY s.region,s.size_id''', (item_code,))
    if rows:
        return rows
    try:
        _, brand_rows = brand_catalog.product(item_code,only_bottoms=True)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    return [{'size_id':None,'garment_id':None,'size_label':row['size_label'],
             'region':'KR','selection_mode':'item_code_size_label'} for row in brand_rows]


@app.get('/api/garments/brand-catalog')
def brand_products():
    return brand_catalog.catalog()


def render_brand(choice, subject):
    try:
        _, rows = brand_catalog.product(choice.item_code,only_bottoms=True)
        if not rows:
            raise HTTPException(404,'Unknown garment and size combination')
        if choice.garment_id is not None or choice.size_id is not None:
            raise HTTPException(422,'Brand-table products require item_code and exact size_label; no numeric IDs exist')
        selected = [row for row in rows if row['size_label']==choice.size_label]
        if len(selected)!=1:
            raise HTTPException(422,'size_label is missing or ambiguous; use the exact database label')
        row = selected[0]
        category = brand_catalog.CATEGORY.get(row['category'])
        recipe = generation_settings(category,[])
        spec = {}  # 하의는 선택 상품의 치수를 적용하지 않고 원형을 그대로 내보냅니다.
        resolve_template(recipe['template_id'],recipe['kind'])
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
    return render({'item_code':choice.item_code,'size_label':row['size_label'],'region':'KR',
                   'spec':spec,'recipe':recipe,'measurement_source':row['source_name'],
                   'measurement_notes':row['notes'],'body_model_id':choice.body_model_id,
                   'geometry_mode':'sam_body' if choice.body_model_id else 'static'},'garment_worker.py',subject=subject)

@app.get("/api/garments/{garment_id}/sizes")
def sizes(garment_id:int):
    return query("SELECT size_id,size_label,region FROM garment.sizes WHERE garment_id=? ORDER BY region,size_id",(garment_id,))

@app.post("/api/garments",response_class=JSONResponse)
def garment(choice:Selection, subject:str=Depends(principal)):
    condition = 'g.item_code=?' if choice.item_code is not None else 'g.garment_id=?'
    parameters = [choice.item_code if choice.item_code is not None else choice.garment_id,
                  choice.size_id if choice.size_id is not None else choice.size_label]
    measurement_columns = '' if choice.body_model_id else ',m.measure_code,m.value_cm'
    measurement_join = '' if choice.body_model_id else " LEFT JOIN garment.measures m ON m.size_id=s.size_id AND m.basis='garment'"
    statement = """SELECT g.garment_id,g.item_code,g.category,g.source_name,
        s.region,s.size_label""" + measurement_columns + """
        FROM garment.garments g JOIN garment.sizes s ON s.garment_id=g.garment_id
        """ + measurement_join + ' WHERE ' + condition + (' AND s.size_id=?' if choice.size_id is not None else " AND s.size_label=? AND s.region='KR'")
    if choice.item_code is not None and choice.garment_id is not None:
        statement += ' AND g.garment_id=?'
        parameters.append(choice.garment_id)
    rows = query(statement, tuple(parameters))
    if not rows:
        if choice.item_code is not None:
            return render_brand(choice,subject)
        raise HTTPException(404,"Unknown garment and size combination")
    if choice.size_label is not None and rows[0]['size_label']!=choice.size_label:
        raise HTTPException(422,'size_label does not match size_id')
    item = rows[0]['item_code']
    try:
        kind, template_id = category_template(rows[0]['category'])
        if choice.body_model_id:
            entry = resolve_template(template_id,kind)
            recipe = {'kind':kind,'template_id':template_id,
                      'sleeve_basis':entry.get('sleeve_basis','none' if kind=='slacks' else 'center_back')}
        else:
            aliases = query('SELECT alias_name FROM ref.measure_aliases WHERE source_name=? AND measure_code=?',
                            (rows[0]['source_name'], 'sleeve_length')) if kind == 'crewneck' else []
            recipe = generation_settings(rows[0]['category'], [row['alias_name'] for row in aliases])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    spec = {}
    for row in rows if kind=='crewneck' and not choice.body_model_id else []:
        code = row['measure_code']
        if code not in LIMITS[kind] or row['value_cm'] is None:
            continue
        value = float(row['value_cm'])
        if not math.isfinite(value) or not 0 < value < 500 or code in spec:
            raise HTTPException(422,"Invalid or duplicate garment measurement: "+str(code))
        spec[code] = value
    try:
        if kind=='crewneck' and not choice.body_model_id:
            spec = validate_spec(recipe['kind'], spec, recipe['sleeve_basis'])
        if not choice.body_model_id:
            resolve_template(recipe.get('template_id'), recipe['kind'])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return render({"garment_id":rows[0]['garment_id'],"size_id":choice.size_id,"item_code":item,"region":rows[0]['region'],
                   "size_label":rows[0]['size_label'],"spec":spec,"recipe":recipe,
                   "body_model_id":choice.body_model_id,
                   "geometry_mode":"sam_body" if choice.body_model_id else "catalog_size"},'garment_worker.py',subject=subject)

@app.get("/demo", include_in_schema=False)
def demo():
    from fastapi.responses import FileResponse
    return FileResponse(ROOT / "demo.html")

app.include_router(downloads('garments'))


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok", "service": "garment"}

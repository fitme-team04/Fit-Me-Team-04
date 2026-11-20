# 목적: 치수 입력 화면의 칸 이름·도움말 — 신체 치수 항목마다 한글 이름 + "옷의 어느 치수와 비교하는지" 안내 글
# 누가 쓰나: 프론트
# 난이도: 심화 — ref.measure_definitions 를 두 번 쓰는 LEFT JOIN (신체 항목 → measure_maps → 옷 항목 한글 이름)
# 출력: 치수 입력칸 표(name·label·part·help, 단면×2 비교 안내) 전체 25행, 몸통 탭(torso) 15행
# 실행: .venv/bin/python db/예시_코드/front/2_심화/04_치수입력_도움말.py
import sys
from pathlib import Path

# 예시_코드 폴더 (_db.py 있는 곳): 이 파일 → 2_심화 → front → 예시_코드
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _db import query, show

PART_NAMES = {"full": "전신", "neck": "목", "torso": "몸통", "arm": "팔", "leg": "다리"}


# 목적: 신체(basis = body) 치수 항목 + 대응하는 옷 항목. body_part 를 주면 그 부위만 (화면의 부위 탭)
def input_fields(body_part=None):
    sql = """
        SELECT d.measure_code, d.korean_name, d.body_part, d.measure_type,
               mm.factor, gd.measure_code AS garment_code, gd.korean_name AS garment_name
        FROM ref.measure_definitions AS d
        LEFT JOIN ref.measure_maps AS mm         ON mm.body_measure_code = d.measure_code
        LEFT JOIN ref.measure_definitions AS gd  ON gd.measure_code = mm.garment_measure_code
        WHERE d.basis = 'body'
          AND d.body_part LIKE %s
        ORDER BY FIELD(d.body_part, 'full', 'neck', 'torso', 'arm', 'leg'), d.measure_code
    """
    part = "%"
    if body_part is not None:
        part = body_part
    return query(sql, (part,))


# 목적: 항목 한 줄 → 칸 도움말 글 (옷 비교에 쓰는 항목인지 알려 줌)
def help_text(row):
    if row["garment_code"] is None:
        return "추천 비교에는 아직 안 씀 (3D·추정용)"
    factor = float(row["factor"])
    if factor == 1.0:
        return "옷 치수 '" + row["garment_name"] + "' 값과 그대로 비교"
    return "옷 치수 '" + row["garment_name"] + "' × " + str(factor) + " 값과 비교 (단면 → 둘레)"


# 목적: 화면에 그릴 칸 목록 [{"name", "label", "part", "help"}]
def field_list(body_part=None):
    fields = []
    for row in input_fields(body_part):
        fields.append({"name": row["measure_code"], "label": row["korean_name"] + " (cm)",
                       "part": PART_NAMES.get(row["body_part"], row["body_part"]), "help": help_text(row)})
    return fields


if __name__ == "__main__":
    show("치수 입력칸 + 도움말 (전체)", field_list())
    show("치수 입력칸 + 도움말 (몸통 탭, body_part = torso)", field_list("torso"))

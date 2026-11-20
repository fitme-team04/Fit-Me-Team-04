-- 브랜드·카테고리별 상품 목록 (사이즈 개수 포함)
-- 바꿀 값: @brand_name, @category (NULL 이면 전체)
SET @brand_name = 'UNIQLO', @category = NULL;

SELECT g.garment_id, b.brand_name, g.category, g.target_gender, g.fit,
       g.garment_name, g.source_name, g.item_code, COUNT(s.size_id) AS size_tally
FROM garment.garments AS g
JOIN garment.brands AS b ON b.brand_id = g.brand_id
LEFT JOIN garment.sizes AS s ON s.garment_id = g.garment_id
WHERE (@brand_name IS NULL OR b.brand_name = @brand_name)
  AND (@category IS NULL OR g.category = @category)
GROUP BY g.garment_id, b.brand_name
ORDER BY b.brand_name, g.category, g.garment_name;

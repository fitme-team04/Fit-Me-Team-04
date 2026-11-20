# 역할: Azure CLI 계정으로 SQL 상품 스키마를 읽기 전용 점검하고 토큰 없이 로컬 보고서를 저장합니다.
param(
    [string]$Server = 'fitme-sql-dev.database.windows.net',
    [string]$Database = 'fitme',
    [string]$Output = 'garment/.cache/sql-catalog-audit.json'
)
$ErrorActionPreference = 'Stop'
$tokenJson = az account get-access-token --resource https://database.windows.net/ --output json
if ($LASTEXITCODE -ne 0) { throw 'Azure CLI SQL token acquisition failed; sign in again.' }
$credential = $tokenJson | ConvertFrom-Json
$connection = New-Object System.Data.SqlClient.SqlConnection
$connection.ConnectionString = "Server=tcp:$Server,1433;Database=$Database;Encrypt=True;TrustServerCertificate=False;Connection Timeout=20;Application Name=FitMeReadOnlyCatalogAudit"
$connection.AccessToken = $credential.accessToken
$credential = $null
$tokenJson = $null
function Read-Rows([string]$Sql) {
    if ($Sql -notmatch '^\s*SELECT\b') { throw 'Only SELECT statements are allowed.' }
    $command = $connection.CreateCommand()
    $command.CommandText = $Sql
    $command.CommandTimeout = 30
    $reader = $command.ExecuteReader()
    try {
        while ($reader.Read()) {
            $row = [ordered]@{}
            for ($i = 0; $i -lt $reader.FieldCount; $i++) {
                $row[$reader.GetName($i)] = if ($reader.IsDBNull($i)) { $null } else { $reader.GetValue($i) }
            }
            [pscustomobject]$row
        }
    } finally { $reader.Dispose(); $command.Dispose() }
}
try {
    $connection.Open()
    $objects = @(Read-Rows "SELECT s.name AS schema_name,o.name AS object_name,o.type_desc FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id WHERE s.name IN ('garment','ref') AND o.type IN ('U','V') ORDER BY s.name,o.name")
    $columns = @(Read-Rows "SELECT s.name AS schema_name,o.name AS object_name,c.name AS column_name,t.name AS data_type,c.is_nullable FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.columns c ON c.object_id=o.object_id JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE s.name IN ('garment','ref') AND o.type IN ('U','V') ORDER BY s.name,o.name,c.column_id")
    $report = [ordered]@{ server=$Server; database=$Database; objects=$objects; columns=$columns }
    $report['catalog'] = @(Read-Rows "SELECT TOP (1000) g.garment_id,g.item_code,g.garment_name,g.category,g.source_name,b.brand_name,s.size_id,s.size_label,s.region,(SELECT COUNT(*) FROM garment.measures m WHERE m.size_id=s.size_id AND m.basis='garment') AS garment_measure_count FROM garment.garments g LEFT JOIN garment.brands b ON b.brand_id=g.brand_id LEFT JOIN garment.sizes s ON s.garment_id=g.garment_id ORDER BY g.garment_id,s.size_id")
    $report['measure_codes'] = @(Read-Rows "SELECT measure_code,basis,COUNT(*) AS row_count FROM garment.measures GROUP BY measure_code,basis ORDER BY measure_code,basis")
    $report['brand_measure_coverage'] = @(Read-Rows "SELECT b.brand_name,COUNT(DISTINCT g.garment_id) AS products,COUNT(DISTINCT s.size_id) AS sizes,COUNT(*) AS measure_rows FROM garment.measures m JOIN garment.sizes s ON s.size_id=m.size_id JOIN garment.garments g ON g.garment_id=s.garment_id LEFT JOIN garment.brands b ON b.brand_id=g.brand_id WHERE m.basis='garment' GROUP BY b.brand_name ORDER BY b.brand_name")
    $report['uniqlo_measure_codes'] = @(Read-Rows "SELECT m.measure_code,m.basis,COUNT(*) AS row_count FROM garment.measures m JOIN garment.sizes s ON s.size_id=m.size_id JOIN garment.garments g ON g.garment_id=s.garment_id JOIN garment.brands b ON b.brand_id=g.brand_id WHERE b.brand_name='UNIQLO' GROUP BY m.measure_code,m.basis ORDER BY m.basis,m.measure_code")
    $report['aliases'] = @(Read-Rows "SELECT TOP (2000) source_name,alias_name,measure_code FROM ref.measure_aliases ORDER BY source_name,measure_code")
    $report['all_columns'] = @(Read-Rows "SELECT s.name AS schema_name,o.name AS object_name,c.name AS column_name,t.name AS data_type FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.columns c ON c.object_id=o.object_id JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE o.type IN ('U','V') AND o.is_ms_shipped=0 ORDER BY s.name,o.name,c.column_id")
    $report['measurement_definitions'] = @(Read-Rows "SELECT measure_code,korean_name,measure_type,basis,iso_clause FROM ref.measure_definitions WHERE measure_code IN ('body_length','sleeve_length','garment_shoulder_width')")
    $report['uniqlo_sleeve_samples'] = @(Read-Rows "SELECT g.item_code,s.size_label,s.region,MAX(CASE WHEN m.measure_code='garment_shoulder_width' THEN m.value_cm END) AS shoulder_cm,MAX(CASE WHEN m.measure_code='sleeve_length' THEN m.value_cm END) AS sleeve_cm,MAX(CASE WHEN m.measure_code='body_length' THEN m.value_cm END) AS body_length_cm,MAX(CASE WHEN m.measure_code='chest_width' THEN m.value_cm END) AS chest_width_cm FROM garment.garments g JOIN garment.sizes s ON s.garment_id=g.garment_id JOIN garment.measures m ON m.size_id=s.size_id AND m.basis='garment' WHERE g.item_code IN ('E422992-000','E465193-000') AND s.size_label='M' GROUP BY g.item_code,s.size_label,s.region ORDER BY g.item_code,s.region")
    $report['schema_descriptions'] = @(Read-Rows "SELECT OBJECT_SCHEMA_NAME(ep.major_id) AS schema_name,OBJECT_NAME(ep.major_id) AS object_name,ep.name,CONVERT(nvarchar(2000),ep.value) AS description FROM sys.extended_properties ep WHERE ep.class=1")
    foreach ($name in @('size_musinsa_standard','size_topten','size_ziozia')) {
        $report[$name] = @(Read-Rows "SELECT TOP (100) category,product_id,product_name,size_label,chest_girth_cm,shoulder_width_cm,arm_length_cm,waist_girth_cm,hip_girth_cm,thigh_girth_cm,inseam_cm,notes,source_name FROM garment.$name ORDER BY product_id,size_label")
    }
    $parent = Split-Path -Parent $Output
    if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Output -Encoding UTF8
    [pscustomobject]@{ connected=$true; objects=$objects.Count; columns=$columns.Count; report=$Output } | ConvertTo-Json
} catch {
    $cause = $_.Exception.GetBaseException()
    if ($cause -is [System.Data.SqlClient.SqlException]) {
        [pscustomobject]@{connected=$false;sql_error=$cause.Number;message=$cause.Message} | ConvertTo-Json
        exit 1
    }
    throw
} finally {
    $connection.Dispose()
}

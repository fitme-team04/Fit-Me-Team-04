-- 역할: 검토·명시적 활성화 후 dbo 예제 상품 테이블만 제거합니다.
-- Explicitly opt in only AFTER verifying these dbo tables are sample copies.
-- No database or garment.* source table is deleted by this script.
SET XACT_ABORT ON;
DECLARE @ConfirmedSampleCopies bit = 0; -- Change to 1 after reviewing contents/dependencies.
IF DB_NAME() <> N'fitme' THROW 51000, 'Select the fitme DB.', 1;
IF @ConfirmedSampleCopies <> 1
    THROW 51001, 'Review dbo catalog contents, backup and dependencies before enabling deletion.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID(N'garment.garments', N'U') IS NULL
       OR OBJECT_ID(N'garment.sizes', N'U') IS NULL
       OR OBJECT_ID(N'garment.measures', N'U') IS NULL
        THROW 51002, 'Production garment tables must exist before removing sample copies.', 1;
    IF OBJECT_ID(N'dbo.measures', N'U') IS NOT NULL DROP TABLE dbo.measures;
    IF OBJECT_ID(N'dbo.sizes', N'U') IS NOT NULL DROP TABLE dbo.sizes;
    IF OBJECT_ID(N'dbo.garments', N'U') IS NOT NULL DROP TABLE dbo.garments;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

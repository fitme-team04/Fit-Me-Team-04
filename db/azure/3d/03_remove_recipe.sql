-- 역할: category·측정 별칭 기반 코드로 전환한 뒤 비어 있는 레시피 테이블만 제거합니다.
-- Deploy the updated garment API before running this on a live service.
SET XACT_ABORT ON;
IF DB_NAME() <> N'fitme' THROW 51000, 'Select the fitme database.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID(N'fitme.fitme_recipe',N'U') IS NOT NULL
    BEGIN
        IF EXISTS(SELECT 1 FROM fitme.fitme_recipe WITH (TABLOCKX,HOLDLOCK))
            THROW 51001, 'Recipe table is no longer empty; review data before removal.', 1;
        DROP TABLE fitme.fitme_recipe;
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
SELECT CASE WHEN OBJECT_ID(N'fitme.fitme_recipe',N'U') IS NULL THEN 1 ELSE 0 END AS recipe_removed;

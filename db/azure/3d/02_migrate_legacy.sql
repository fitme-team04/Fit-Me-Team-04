-- 역할: 기존 dbo 서비스 테이블을 fitme 스키마로 옮깁니다.
-- Existing fitme DB only. Moves service tables without copying/deleting rows.
-- Stop API + Azure ML writes and take a DB backup before deployment.
SET XACT_ABORT ON;
IF DB_NAME() <> N'fitme' THROW 51000, 'Select the fitme DB.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    IF SCHEMA_ID(N'fitme') IS NULL EXEC(N'CREATE SCHEMA fitme AUTHORIZATION dbo;');
    DECLARE @name sysname;
    DECLARE tables_to_move CURSOR LOCAL FAST_FORWARD FOR
        SELECT name FROM (VALUES (N'fitme_request'), (N'fitme_prediction'),
            (N'fitme_measure_definition')) t(name);
    OPEN tables_to_move;
    FETCH NEXT FROM tables_to_move INTO @name;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        IF OBJECT_ID(N'dbo.' + @name, N'U') IS NOT NULL
        BEGIN
            IF OBJECT_ID(N'fitme.' + @name) IS NOT NULL
                THROW 51001, 'Both dbo and fitme service objects exist. Resolve before migrating.', 1;
            EXEC(N'ALTER SCHEMA fitme TRANSFER dbo.' + QUOTENAME(@name) + N';');
        END;
        FETCH NEXT FROM tables_to_move INTO @name;
    END;
    CLOSE tables_to_move;
    DEALLOCATE tables_to_move;
    -- Remove only obsolete catalog views. Existing tables require separate review.
    IF OBJECT_ID(N'dbo.measures', N'V') IS NOT NULL EXEC(N'DROP VIEW dbo.measures;');
    IF OBJECT_ID(N'dbo.sizes', N'V') IS NOT NULL EXEC(N'DROP VIEW dbo.sizes;');
    IF OBJECT_ID(N'dbo.garments', N'V') IS NOT NULL EXEC(N'DROP VIEW dbo.garments;');
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
-- ALTER SCHEMA drops explicit object permissions. Regrant the API/ML identities
-- appropriate permissions on SCHEMA::fitme, and API SELECT on SCHEMA::garment.
-- dbo is a SQL Server system schema: do not attempt to DROP SCHEMA dbo.

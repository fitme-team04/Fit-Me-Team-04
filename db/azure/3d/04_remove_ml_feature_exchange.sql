-- 역할: JSON 직접 전달로 전환하면서 이번 작업에서 만든 빈 임시 테이블과 전용 사용자를 정리합니다.
SET XACT_ABORT ON;
DECLARE @expected_sid binary(16) = CONVERT(binary(16), CONVERT(uniqueidentifier, '00000000-0000-0000-0000-000000000000'));
IF EXISTS (SELECT 1 FROM sys.database_principals
           WHERE name=N'fitme-vm-body-dev' AND (sid<>@expected_sid OR type<>'E'))
    THROW 51000, 'VM SQL identity changed; cancellation stopped.', 1;
IF OBJECT_ID(N'fitme.ml_feature_requests', N'U') IS NOT NULL
BEGIN
    IF EXISTS (SELECT 1 FROM fitme.ml_feature_requests)
        THROW 51001, 'Temporary table contains rows; cancellation stopped.', 1;
    DROP TABLE fitme.ml_feature_requests;
END;
-- 다른 권한·역할·소유권이 추가된 사용자는 삭제하지 않습니다.
DECLARE @principal int = DATABASE_PRINCIPAL_ID(N'fitme-vm-body-dev');
IF @principal IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM sys.database_permissions WHERE grantee_principal_id=@principal
                   AND NOT (class=0 AND permission_name='CONNECT' AND state='G'))
   AND NOT EXISTS (SELECT 1 FROM sys.database_role_members WHERE member_principal_id=@principal)
   AND NOT EXISTS (SELECT 1 FROM sys.schemas WHERE principal_id=@principal)
   AND NOT EXISTS (SELECT 1 FROM sys.objects WHERE principal_id=@principal)
BEGIN
    DROP USER [fitme-vm-body-dev];
END;

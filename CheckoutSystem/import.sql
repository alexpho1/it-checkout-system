use ITCheckoutSystem;
--update enduser table and fill. initial import
GO
ALTER TABLE ENDUSER
ADD OBJECTGUID UNIQUEIDENTIFIER

GO
CREATE UNIQUE NONCLUSTERED INDEX IX_ENDUSER_OBJECTGUID ON dbo.ENDUSER (OBJECTGUID) 
WHERE OBJECTGUID IS NOT NULL

GO
CREATE TABLE stg_ADUsers
(
    OBJECTGUID VARCHAR(36),
    ADusername VARCHAR(20), 
    FullName VARCHAR(40),
    Email VARCHAR(50),
    IsActive BIT,
    LoadedAt DATETIME2 DEFAULT SYSDATETIME()
)
CREATE TABLE import_log
(
    ImportID INT PRIMARY KEY IDENTITY(1,1),
    ImportDate DATETIME NOT NULL DEFAULT GETDATE(),
    RowsLoaded INT,
    RecordsInserted INT,
    RecordsUpdated INT,
    RecordsDisabled INT,
    Status VARCHAR(20) NOT NULL,
    ErrorMessage VARCHAR(255)
)

GO
CREATE OR ALTER PROCEDURE sp_ImportADUsers
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
        DECLARE @RecordsLoaded INT = 0;
        DECLARE @RecordsInserted INT = 0;
        DECLARE @RecordsUpdated INT = 0;
        DECLARE @RecordsDisabled INT = 0;
    BEGIN TRY
        IF EXISTS (SELECT OBJECTGUID, ADusername FROM stg_ADUsers WHERE OBJECTGUID IS NULL OR LTRIM(RTRIM(OBJECTGUID)) = '' OR LTRIM(RTRIM(ADusername)) = '' OR ADusername IS NULL )
        BEGIN
            THROW 50011, 'Validation Error: OBJECTGUID or ADusername is NULL or empty in stg_ADUsers.', 1;
        END 
        IF EXISTS (SELECT OBJECTGUID FROM stg_ADUsers WHERE TRY_CAST(OBJECTGUID AS UNIQUEIDENTIFIER) IS NULL AND OBJECTGUID IS NOT NULL AND LTRIM(RTRIM(OBJECTGUID)) <> '')
        BEGIN
            THROW 50012, 'Validation Error: OBJECTGUID is not a valid GUID in stg_ADUsers.', 1;
        END
        IF EXISTS (SELECT OBJECTGUID FROM stg_ADUsers GROUP BY OBJECTGUID HAVING COUNT(*) > 1)
        BEGIN
            THROW 50013, 'Validation Error: Duplicate OBJECTGUID found in stg_ADUsers.', 1;
        END
        IF EXISTS (SELECT ADusername FROM stg_ADUsers GROUP BY ADusername HAVING COUNT(*) > 1)
        BEGIN
            THROW 50014, 'Validation Error: Duplicate ADusername found in stg_ADUsers.', 1;
        END
        IF EXISTS (SELECT OBJECTGUID FROM stg_ADUsers WHERE IsActive IS NULL)
        BEGIN
            THROW 50015, 'Validation Error: IsActive is NULL in stg_ADUsers.', 1;
        END
        IF NOT EXISTS (SELECT 1 FROM stg_ADUsers)
        BEGIN
            THROW 50016, 'Validation Error: No rows were loaded', 1;
        END
        BEGIN TRANSACTION;

            UPDATE e
            SET e.OBJECTGUID =  TRY_CAST(s.OBJECTGUID AS UNIQUEIDENTIFIER)
            FROM ENDUSER e
            JOIN stg_ADUsers s on e.ADusername = s.ADusername
            WHERE e.OBJECTGUID IS NULL;

            UPDATE e
            SET e.ADusername = s.ADusername,
                e.FullName = s.FullName,
                e.Email = s.Email,
                e.IsActive = s.IsActive
            FROM ENDUSER e
            JOIN stg_ADUsers s ON e.OBJECTGUID = TRY_CAST(s.OBJECTGUID AS UNIQUEIDENTIFIER)
            WHERE ISNULL(e.ADusername, '') <> ISNULL(s.ADusername, '') OR ISNULL(e.FullName, '') <> ISNULL(s.FullName, '') OR ISNULL(e.Email, '') <> ISNULL(s.Email, '') OR ISNULL(e.IsActive, 0) <> ISNULL(s.IsActive, 0);
            SET @RecordsUpdated = @@ROWCOUNT;

            INSERT INTO ENDUSER (OBJECTGUID, ADusername, FullName, Email, IsActive)
            SELECT TRY_CAST(OBJECTGUID AS UNIQUEIDENTIFIER), ADusername, FullName, Email, IsActive
            FROM stg_ADUsers s
            WHERE NOT EXISTS (SELECT 1 FROM ENDUSER e WHERE e.OBJECTGUID = TRY_CAST(s.OBJECTGUID AS UNIQUEIDENTIFIER));
            SET @RecordsInserted = @@ROWCOUNT;

            UPDATE e
            SET e.IsActive = 0
            FROM ENDUSER e
            WHERE e.IsActive = 1 AND e.OBJECTGUID IS NOT NULL AND NOT EXISTS (SELECT 1 FROM stg_ADUsers s WHERE e.OBJECTGUID = TRY_CAST(s.OBJECTGUID AS UNIQUEIDENTIFIER) AND s.IsActive = 1);
            SET @RecordsDisabled = @@ROWCOUNT;

            INSERT INTO import_log (RowsLoaded, RecordsInserted, RecordsUpdated, RecordsDisabled, Status)
            VALUES (@RecordsLoaded, @RecordsInserted, @RecordsUpdated, @RecordsDisabled, 'Success');
            COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0
        BEGIN
            ROLLBACK TRANSACTION;
        END;
        INSERT INTO import_log (RowsLoaded, RecordsInserted, RecordsUpdated, RecordsDisabled, Status, ErrorMessage)
        VALUES (@RecordsLoaded, NULL, NULL, NULL, 'Failed', LEFT(ERROR_MESSAGE(), 255));
        THROW;
    END CATCH
END

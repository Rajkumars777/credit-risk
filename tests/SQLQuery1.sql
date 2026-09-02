CREATE DATABASE [ltid];
GO

USE [ltid];
GO

create table customer (
    "Application No" INT,
    "Party No" INT,
    AmountFinance       DECIMAL(18,2) NULL,
    Downpayment         DECIMAL(18,2) NULL,
    DownpaymentPercent  DECIMAL(5,2)  NULL,
    PaymentTerms        INT           NULL,

    Asset               NVARCHAR(200) NULL,
    Manufacturer        NVARCHAR(200) NULL,
    TypeOfUnit          NVARCHAR(100) NULL,

    PriceGap            DECIMAL(18,2) NULL,
    LoanHistory         NVARCHAR(250) NULL,

    BAPType             NVARCHAR(50)  NULL,
    BAPAmount           DECIMAL(18,2) NULL,
    InterestRate        DECIMAL(12,8) NULL,

    ClaimedIncome       DECIMAL(18,2) NULL,
    EVIncome            DECIMAL(18,2) NULL,
    BVIncome            DECIMAL(18,2) NULL,

    EmploymentType      NVARCHAR(100) NULL,
    ClaimedTenure       DECIMAL(10,2) NULL,
    EVTenure            DECIMAL(10,2) NULL,
    BVTenure            DECIMAL(10,2) NULL,

    DSCR                DECIMAL(12,3) NULL,
    AgeAsOfContract     INT           NULL,

    HomeOwnership       NVARCHAR(100) NULL,
    ResidenceTenure     DECIMAL(10,2) NULL,
    Citizenship         NVARCHAR(100) NULL,

    DealerName          NVARCHAR(200) NULL,
    SubmittedID         NVARCHAR(50)  NULL,
    MaritalStatus       NVARCHAR(50)  NULL,

    LoanAmort           DECIMAL(18,2) NULL,
    ProductType         NVARCHAR(100) NULL,
    ModeOfPayment       NVARCHAR(100) NULL,

    CoBorrowers         NVARCHAR(20)  NULL,
    BorrowerType        NVARCHAR(50)  NULL,

    ContractStartDate   DATE          NULL
);

INSERT INTO dbo.Customer
(
    "Party No",
    "Application No",
    AmountFinance,
    Downpayment,
    DownpaymentPercent,
    PaymentTerms,
    Asset,
    Manufacturer,
    TypeOfUnit,
    PriceGap,
    LoanHistory,
    BAPType,
    BAPAmount,
    InterestRate,
    ClaimedIncome,
    EVIncome,
    BVIncome,
    EmploymentType,
    ClaimedTenure,
    EVTenure,
    BVTenure,
    DSCR,
    AgeAsOfContract,
    HomeOwnership,
    ResidenceTenure,
    Citizenship,
    DealerName,
    SubmittedID,
    MaritalStatus,
    LoanAmort,
    ProductType,
    ModeOfPayment,
    CoBorrowers,
    BorrowerType,
    ContractStartDate
)
VALUES
(   12,
    12444,
    256480.00,
    64120.00,
    20.00,
    48,
    N'Kawasaki Z500 SE',
    N'Kawasaki Philippines',
    N'Non High Risk Unit',
    -32060.00,
    N'Fully paid Good Repeat Client',
    N'Good',
    0.00,
    21.433464216872,
    145000.00,
    NULL, -- EV Income was blank
    NULL, -- BV Income was blank
    N'Locally employed',
    48.00,
    NULL, -- EV Tenure was blank
    NULL, -- BV Tenure was blank
    14.869,
    36,
    N'Mortgaged',
    84.00,
    N'Philippines',
    N'Wheeltek Taytay',
    N'ID2',
    N'Married',
    8002.00,
    N'Bike Loan',
    N'ADA - BPI',
    N'No',
    N'Principal',
    '2025-12-12'
);

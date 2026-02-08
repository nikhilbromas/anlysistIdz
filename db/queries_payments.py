"""Payment mode, split payment, and currency SQL queries."""

# Payment mode analysis
SQL_PAYMENT_MODE = """
SELECT
    h.poshShopID        AS shopid,
    CONVERT(DATE, h.poshBillDate) AS billdate,
    h.poshCashAccID     AS accountid,
    ISNULL(a.AccountDesc, h.poshPaymentMode)  AS payment_mode,
    SUM(h.poshBillAmount)   AS amount,
    COUNT(*)                AS bill_count
FROM LOsPosHeader h
INNER JOIN aShops s  ON s.ShopID = h.poshShopID AND s.futurevarchar = 'f'
LEFT JOIN aAccountMaster a ON a.AccountID = h.poshCashAccID
WHERE h.poshCancelled = 0
GROUP BY h.poshShopID, CONVERT(DATE, h.poshBillDate),
         h.poshCashAccID, ISNULL(a.AccountDesc, h.poshPaymentMode)
"""

# Currency master
SQL_CURRENCY_MASTER = """
SELECT CurrencyID, CurrencyName, Symbol FROM aCurrencyMaster
"""

# Split payment details (per-bill payment breakdown)
SQL_SPLIT_PAYMENT = """
SELECT
    pp.PoshBillid       AS billid,
    pp.PoshShopid       AS shopid,
    CONVERT(DATE, h.poshBillDate) AS billdate,
    h.poshPaymentMode   AS header_mode,
    pp.PoshPaymentAccid AS accountid,
    ISNULL(a.AccountDesc, pp.PaymentType) AS account_name,
    pp.PoshPaymentAmnt  AS amount,
    pp.PaymentType      AS payment_type
FROM PoshPaymentDetails pp
INNER JOIN LOsPosHeader h
    ON h.poshBillID = pp.PoshBillid AND h.poshShopID = pp.PoshShopid
INNER JOIN aShops s
    ON s.ShopID = pp.PoshShopid AND s.futurevarchar = 'f'
LEFT JOIN aAccountMaster a
    ON a.AccountID = pp.PoshPaymentAccid
WHERE h.poshCancelled = 0
"""

# Stored procedure call
SQL_SP_FB_POS_AMT = "EXEC spGetPosAmtDetailForReportFB"

# Sessions (denomination open/close pairs) for session-based filtering
SQL_SESSIONS = """
SELECT
    dh_open.denominationid      AS session_id,
    dh_open.denominationno      AS session_no,
    dh_open.denomdate           AS open_time,
    dh_close.denominationid     AS close_id,
    dh_close.denomdate          AS close_time,
    dh_open.PosBillId           AS start_bill,
    dh_close.PosBillId          AS end_bill,
    dh_open.TillId              AS tillid,
    ISNULL(cm.CounterName, '')  AS counter_name,
    dh_open.shopid,
    ISNULL(u.Name, '')          AS user_name
FROM DenominationHeader dh_open
INNER JOIN DenominationHeader dh_close
    ON dh_close.ParentId = dh_open.denominationid
   AND dh_close.TillOpen = 0 AND dh_close.cancelled = 0
INNER JOIN aShops s ON s.ShopID = dh_open.shopid AND s.futurevarchar = 'f'
LEFT JOIN aCounterMaster cm ON cm.CounterId = dh_open.TillId
LEFT JOIN Users u ON u.SocialUserId = dh_open.denoUserID
WHERE dh_open.TillOpen = 1 AND dh_open.cancelled = 0
ORDER BY dh_open.denominationid DESC
"""

# GST sales from existing view
SQL_GST_SALES = """
SELECT companyid, shopid,
       CONVERT(DATE, billdate) AS billdate,
       accountid,
       amount, damount, camount,
       cash, transtype, departmentid,
       GSTAmount, dGSTAmount, cGSTAmount
FROM vwCAshSalesGSTSeparately
WHERE shopid IN (SELECT ShopID FROM aShops WHERE futurevarchar = 'f')
"""

# Denomination detail (cash counting per session)
SQL_DENOMINATION_DETAIL = """
SELECT
    dd.ddenominationid          AS session_id,
    dd.dshopid                  AS shopid,
    dd.dcurrencyid              AS currencyid,
    ISNULL(cm.CurrencyName, '') AS currencyname,
    ISNULL(cm.Symbol, '')       AS symbol,
    dd.ddenominationtype        AS denomination,
    dd.ddenominationcount       AS deno_count,
    dd.damount                  AS amount,
    dd.ddepamount               AS dep_amount
FROM DenominationDetail dd
LEFT JOIN aCurrencyMaster cm ON cm.CurrencyID = dd.dcurrencyid
INNER JOIN DenominationHeader dh ON dh.denominationid = dd.ddenominationid AND dh.cancelled = 0
INNER JOIN aShops s ON s.ShopID = dd.dshopid AND s.futurevarchar = 'f'
"""

# Day-end sales: bill-level with split payments, tax, service charge, returns
SQL_DAY_END_SALES = """
-- Sales bills
SELECT
    CONVERT(DATE, h.poshBillDate)   AS billdate,
    h.poshBillNo                    AS billno,
    h.poshBillID                    AS billid,
    FORMAT(h.poshBillTime, 'hh:mm tt') AS billtime,
    h.poshShopID                    AS shopid,
    h.poshCounterId                 AS counterid,
    ISNULL(pa.CashAmount, h.poshCashAmount) * h.poshExchangeRate     AS cash_amount,
    ISNULL(pa.CardAmount, h.poshCardAmount) * h.poshExchangeRate     AS card_amount,
    ISNULL(pa.BankAmount, h.poshCardAmount) * h.poshExchangeRate     AS bank_amount,
    ISNULL(pa.CreditAmount, h.poshCreditAmount) * h.poshExchangeRate AS credit_amount,
    ISNULL(pa.PaymentAmount, h.poshBillAmount) * h.poshExchangeRate  AS bill_amount,
    SUM(d.posdItemTaxAmount * h.poshExchangeRate)                    AS tax_amount,
    ISNULL(pa.PaymentAmount, h.poshBillAmount) * h.poshExchangeRate
        - SUM(d.posdItemTaxAmount * h.poshExchangeRate)              AS amount_without_tax,
    0                               AS return_amount,
    ISNULL(se.posoAmount, 0) * h.poshExchangeRate AS service_charge,
    1                               AS view_order
FROM LOsPosHeader h
INNER JOIN LOsPosDetail d
    ON h.poshBillID = d.posdBillID AND h.poshShopID = d.posdShopID
INNER JOIN aShops s
    ON s.ShopID = h.poshShopID AND s.futurevarchar = 'f'
LEFT JOIN (
    SELECT PoshBillid,
        CAST(COALESCE(MAX(CASE WHEN PaymentType='Cash'   THEN PoshPaymentAmnt END), 0) AS DECIMAL(18,2)) AS CashAmount,
        CAST(COALESCE(MAX(CASE WHEN PaymentType='Card'   THEN PoshPaymentAmnt END), 0) AS DECIMAL(18,2)) AS CardAmount,
        CAST(COALESCE(MAX(CASE WHEN PaymentType='Bank'   THEN PoshPaymentAmnt END), 0) AS DECIMAL(18,2)) AS BankAmount,
        CAST(COALESCE(MAX(CASE WHEN PaymentType='Credit' THEN PoshPaymentAmnt END), 0) AS DECIMAL(18,2)) AS CreditAmount,
        CAST(SUM(PoshPaymentAmnt) AS DECIMAL(18,2)) AS PaymentAmount
    FROM PoshPaymentDetails GROUP BY PoshBillid
) pa ON pa.PoshBillid = h.poshBillID
LEFT JOIN LOsPosOthercharges se
    ON se.posoBillID = h.poshBillID AND se.posoShopID = h.poshShopID
WHERE h.poshCancelled = 0
GROUP BY
    d.posdBillID, h.poshBillDate, h.poshBillNo,
    ISNULL(pa.CashAmount, h.poshCashAmount),
    ISNULL(pa.CardAmount, h.poshCardAmount),
    ISNULL(pa.BankAmount, h.poshCardAmount),
    ISNULL(pa.CreditAmount, h.poshCreditAmount),
    ISNULL(pa.PaymentAmount, h.poshBillAmount),
    h.poshShopID, h.poshBillID, h.poshBillTime,
    h.poshExchangeRate, ISNULL(se.posoAmount, 0),
    h.poshCounterId

UNION ALL

-- Returns (negative amounts)
SELECT
    CONVERT(DATE, eh.sehExchangeDate) AS billdate,
    eh.sehExchangeNo              AS billno,
    eh.sehExchangeID              AS billid,
    FORMAT(eh.sehTime, 'hh:mm tt') AS billtime,
    eh.sehShopID                  AS shopid,
    0                             AS counterid,
    0                             AS cash_amount,
    0                             AS card_amount,
    0                             AS bank_amount,
    0                             AS credit_amount,
    -(eh.sehExchangeBillAmount * eh.sehExchangeRate) AS bill_amount,
    -SUM(ed.sedItemTaxAmount * eh.sehExchangeRate)   AS tax_amount,
    -(eh.sehExchangeBillAmount * eh.sehExchangeRate)
        + SUM(ed.sedItemTaxAmount * eh.sehExchangeRate) AS amount_without_tax,
    -(eh.sehExchangeBillAmount * eh.sehExchangeRate) AS return_amount,
    0                             AS service_charge,
    2                             AS view_order
FROM losposExchangeHeader eh
INNER JOIN losposExchangeDetail ed
    ON ed.sedShopID = eh.sehShopID AND ed.sedExchangeID = eh.sehExchangeID
INNER JOIN aShops s
    ON s.ShopID = eh.sehShopID AND s.futurevarchar = 'f'
WHERE eh.sehCancelled = 0
GROUP BY
    eh.sehExchangeDate, eh.sehExchangeNo,
    eh.sehExchangeBillAmount, eh.sehShopID,
    eh.sehExchangeID, eh.sehTime, eh.sehExchangeRate
"""

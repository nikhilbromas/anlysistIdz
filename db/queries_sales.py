"""Sales, service charge, and order-related SQL queries."""

# Restaurant shops only
SQL_RESTAURANT_SHOPS = """
SELECT ShopID, ShopName
FROM aShops
WHERE futurevarchar = 'f'
"""

# Daily sales summary (header level) — with currency cols
SQL_SALES_SUMMARY = """
SELECT
    h.poshShopID                             AS shopid,
    s.ShopName                               AS shopname,
    CONVERT(DATE, h.poshBillDate)            AS billdate,
    COUNT(DISTINCT h.poshBillID)             AS total_bills,
    SUM(h.poshBillAmount)                    AS total_amount,
    SUM(h.poshBillAmount * h.poshdepexrate)  AS total_damount,
    SUM(h.poshBillAmount * h.poshExchangeRate) AS total_camount,
    SUM(h.poshDiscount)                      AS total_discount,
    SUM(ISNULL(h.poshOtherCharge, 0))        AS total_service_charge,
    AVG(h.poshBillAmount)                    AS avg_bill_value,
    SUM(ISNULL(h.poshCashAmount, 0))         AS total_cash,
    SUM(ISNULL(h.poshCardAmount, 0))         AS total_card,
    SUM(ISNULL(h.poshCreditAmount, 0))       AS total_credit
FROM LOsPosHeader h
INNER JOIN aShops s
    ON s.ShopID = h.poshShopID AND s.futurevarchar = 'f'
WHERE h.poshCancelled = 0
GROUP BY h.poshShopID, s.ShopName, CONVERT(DATE, h.poshBillDate)
"""

# Sales bill-level (for session filtering — includes billid and counterid)
SQL_SALES_BILL_LEVEL = """
SELECT
    h.poshShopID                AS shopid,
    s.ShopName                  AS shopname,
    h.poshBillID                AS billid,
    h.poshCounterId             AS counterid,
    CONVERT(DATE, h.poshBillDate) AS billdate,
    h.poshBillAmount            AS total_amount,
    h.poshBillAmount * h.poshdepexrate  AS total_damount,
    h.poshBillAmount * h.poshExchangeRate AS total_camount,
    h.poshDiscount              AS total_discount,
    ISNULL(h.poshOtherCharge, 0) AS total_service_charge,
    ISNULL(h.poshCashAmount, 0) AS total_cash,
    ISNULL(h.poshCardAmount, 0) AS total_card,
    ISNULL(h.poshCreditAmount, 0) AS total_credit
FROM LOsPosHeader h
INNER JOIN aShops s
    ON s.ShopID = h.poshShopID AND s.futurevarchar = 'f'
WHERE h.poshCancelled = 0
"""

# Sales detail (item level) — with packingtype
SQL_SALES_DETAIL = """
SELECT
    d.posdShopID                        AS shopid,
    d.posdBillID                        AS billid,
    d.posdItemID                        AS itemid,
    ISNULL(im.ItemDescription, '')      AS itemname,
    ISNULL(pt.PackingTypeName, '')      AS packingtype,
    d.posdQuantity                      AS qty,
    d.posdUnitPrice                     AS rate,
    d.posdQuantity * d.posdUnitPrice    AS amount,
    d.posdcostprice                     AS costprice,
    d.posdItemType                      AS item_type,
    CONVERT(DATE, h.poshBillDate)       AS billdate,
    h.poshBillNo                        AS billno
FROM LOsPosDetail d
INNER JOIN LOsPosHeader h
    ON h.poshBillID = d.posdBillID AND h.poshShopID = d.posdShopID
INNER JOIN aShops s
    ON s.ShopID = h.poshShopID AND s.futurevarchar = 'f'
LEFT JOIN aItem im
    ON im.ItemID = d.posdItemID
LEFT JOIN aPackingType pt
    ON pt.PackingTypeID = d.posdPackingTypeID
WHERE h.poshCancelled = 0
"""

# Service charge report
SQL_SERVICE_CHARGE = """
SELECT
    posh.poshCompanyID              AS companyid,
    posh.poshShopID                 AS shopid,
    posh.poshBillDate               AS billdate,
    posh.poshCashAccID              AS accountid,
    CONVERT(NUMERIC(18,9), SUM(se.posoAmount))                             AS amount,
    CONVERT(NUMERIC(18,9), SUM(se.posoAmount) * posh.poshdepexrate)        AS damount,
    CONVERT(NUMERIC(18,9), SUM(se.posoAmount) * posh.poshExchangeRate)     AS camount,
    1                               AS cash,
    'sc'                            AS transtype,
    posh.poshDepartmentid           AS departmentid,
    0                               AS PdChqCancelled,
    ISNULL(posh.poshUserId, 0)      AS UserID,
    ISNULL(rs.TotalTaxPercentage, 16) AS TaxPercentage,
    ISNULL(posh.poshOtherCharge, 0)                              AS TaxAmount,
    ISNULL(posh.poshOtherCharge * posh.poshdepexrate, 0)         AS DTaxAmount,
    ISNULL(posh.poshOtherCharge * posh.poshExchangeRate, 0)      AS CTaxAmount,
    posh.poshBillNo,
    0                               AS posdItemTaxCategory,
    posh.poshCustomerName,
    posh.poshCustomerTIN
FROM LOsPosHeader posh
INNER JOIN LOsPosOthercharges se
    ON se.posoBillID = posh.poshBillID
   AND se.posoShopID = posh.poshShopID
LEFT JOIN (
    SELECT BillId, ShopId,
           MAX(TotalTaxPercentage) AS TotalTaxPercentage,
           0 AS TotalTaxAmount
    FROM RestaurantServiceTaxTransaction
    WHERE IsCancelled = 0
    GROUP BY BillId, ShopId
) rs
    ON rs.BillId  = posh.poshBillID
   AND rs.ShopId  = posh.poshShopID
WHERE posh.poshCancelled = 0
  AND se.posoDescription = 'Service Charge'
  AND se.posoAmount > 0
GROUP BY
    posh.poshCompanyID, posh.poshShopID, posh.poshBillDate,
    posh.poshBillID, posh.poshCashAccID, posh.poshDepartmentid,
    posh.poshdepexrate, posh.poshExchangeRate,
    ISNULL(posh.poshUserId, 0), posh.poshBillNo,
    posh.poshCustomerName, posh.poshCustomerTIN,
    rs.TotalTaxPercentage, rs.TotalTaxAmount,
    posh.poshOtherCharge
"""

# Order / ingredient consumption report — with packingtype
SQL_ORDER_INGREDIENT = """
SELECT
    ph.poshShopID                           AS shopid,
    il.ItemID                               AS itemid,
    ISNULL(im.ItemDescription, '')          AS itemname,
    ISNULL(pt.PackingTypeName, '')          AS packingtype,
    CONVERT(DATETIME, CONVERT(VARCHAR(10), ph.poshBillDate, 111)) AS sdate,
    ph.poshBillNo + '(order/' + CAST(oh.OrderID AS VARCHAR) + ')' AS poshBillNo,
    ph.poshBillID                           AS transid,
    CONVERT(NUMERIC(18,3), il.Qty)          AS cashsales,
    'F and B Sales'                         AS type,
    -1                                      AS mode,
    ph.updatetime,
    ISNULL(il.CostingValue, 0)              AS costprice,
    ISNULL(il.CostingValue, 0) * ph.poshdepexrate    AS depcostprice,
    ISNULL(il.CostingValue, 0) * ph.poshExchangeRate  AS concostprice,
    ''                                      AS from_to,
    ISNULL(ph.poshCustomerName, 'CASH')     AS customername
FROM LOsPosDetail pd
INNER JOIN LOsPosHeader ph
    ON ph.poshBillID = pd.posdBillID AND ph.poshShopID = pd.posdShopID
INNER JOIN OrderHeader oh
    ON oh.BillID = ph.poshBillID AND oh.ShopID = ph.poshShopID
LEFT JOIN IngredientDetails il
    ON pd.posdItemID = il.MenuItemID AND il.BillId = ph.poshBillID
LEFT JOIN aItem im
    ON il.ItemID = im.ItemID
LEFT JOIN aPackingType pt
    ON pt.PackingTypeID = il.PackingTypeID
INNER JOIN aShops s
    ON s.ShopID = ph.poshShopID AND s.futurevarchar = 'f'
WHERE ph.poshCancelled = 0
  AND pd.posdItemType = 'f'
  AND il.Qty > 0
"""

# Order header (restaurant shops only)
SQL_ORDER_HEADER = """
SELECT
    oh.OrderID,
    oh.ShopID,
    oh.BillID,
    oh.TableID,
    oh.TableName,
    oh.OrderType,
    oh.OrderStatus,
    oh.CreatedAt,
    oh.IsActive
FROM OrderHeader oh
INNER JOIN aShops s ON s.ShopID = oh.ShopID AND s.futurevarchar = 'f'
"""

# Order details (restaurant shops only)
SQL_ORDER_DETAILS = """
SELECT
    od.OrderID,
    od.ShopID,
    od.BillID,
    od.ItemID,
    od.ItemName,
    od.Qty,
    od.CreatedAt,
    od.IsActive
FROM OrderDetails od
INNER JOIN OrderHeader oh ON oh.OrderID = od.OrderID AND oh.ShopID = od.ShopID
INNER JOIN aShops s ON s.ShopID = oh.ShopID AND s.futurevarchar = 'f'
"""

# Segment analysis
SQL_SEGMENT_SALES = """
SELECT
    h.poshShopID        AS shopid,
    s.ShopName          AS shopname,
    CONVERT(DATE, h.poshBillDate) AS billdate,
    h.poshSegmentID     AS segmentid,
    ISNULL(seg.SegmentName, 'Unknown') AS segmentname,
    SUM(h.poshBillAmount)   AS amount,
    COUNT(*)                AS bill_count
FROM LOsPosHeader h
INNER JOIN aShops s   ON s.ShopID = h.poshShopID AND s.futurevarchar = 'f'
LEFT JOIN ASegmentMaster seg ON seg.Segmentid = h.poshSegmentID
WHERE h.poshCancelled = 0
GROUP BY h.poshShopID, s.ShopName, CONVERT(DATE, h.poshBillDate),
         h.poshSegmentID, ISNULL(seg.SegmentName, 'Unknown')
"""

# Customer profitability (line-level: revenue, cost, profit per item per bill)
# For FREEBILL with zero unit price, uses aItem.ItemRate as actual price
SQL_CUSTOMER_PROFITABILITY = """
SELECT
    h.poshcustomerid          AS customerid,
    ISNULL(c.CustomerName, h.poshCustomerName) AS customername,
    h.poshPaymentMode         AS payment_mode,
    d.posdItemID              AS itemid,
    ISNULL(im.ItemDescription, '') AS itemname,
    d.posdItemType            AS item_type,
    CONVERT(DATE, h.poshBillDate) AS billdate,
    h.poshBillID              AS billid,
    d.posdQuantity            AS qty,
    CASE WHEN h.poshPaymentMode = 'FREEBILL' AND ISNULL(d.posdUnitPrice, 0) = 0
         THEN ISNULL(im.ItemRate, 0)
         ELSE d.posdUnitPrice END AS unitprice,
    d.posdcostprice           AS costprice
FROM LOsPosDetail d
INNER JOIN LOsPosHeader h
    ON h.poshBillID = d.posdBillID AND h.poshShopID = d.posdShopID
INNER JOIN aShops s
    ON s.ShopID = h.poshShopID AND s.futurevarchar = 'f'
LEFT JOIN aCustomerMaster c
    ON c.CustomerID = h.poshcustomerid
LEFT JOIN aItem im
    ON im.ItemID = d.posdItemID
WHERE h.poshCancelled = 0
"""

# Segment-wise item pricing from actual POS sales (menu items, grouped by segment)
SQL_SEGMENT_ITEM_PRICING = """
SELECT
    h.poshSegmentID             AS segmentid,
    ISNULL(seg.SegmentName, 'No Segment') AS segmentname,
    d.posdItemID                AS itemid,
    ISNULL(im.ItemDescription, '') AS itemname,
    im.itemtype                 AS item_type,
    ISNULL(im.ItemRate, 0)      AS base_rate,
    AVG(d.posdUnitPrice)        AS avg_selling_price,
    AVG(d.posdcostprice)        AS avg_cost_price,
    SUM(d.posdQuantity)         AS total_qty,
    SUM(d.posdQuantity * d.posdUnitPrice)  AS total_revenue,
    SUM(d.posdQuantity * d.posdcostprice)  AS total_cost,
    COUNT(DISTINCT h.poshBillID) AS bill_count
FROM LOsPosDetail d
INNER JOIN LOsPosHeader h
    ON h.poshBillID = d.posdBillID AND h.poshShopID = d.posdShopID
INNER JOIN aShops s
    ON s.ShopID = h.poshShopID AND s.futurevarchar = 'f'
LEFT JOIN ASegmentMaster seg
    ON seg.Segmentid = h.poshSegmentID
LEFT JOIN aItem im
    ON im.ItemID = d.posdItemID
WHERE h.poshCancelled = 0
  AND d.posdItemType = 'f'
GROUP BY h.poshSegmentID, seg.SegmentName,
         d.posdItemID, im.ItemDescription, im.itemtype, im.ItemRate
"""

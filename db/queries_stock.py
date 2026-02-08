"""
Stock movement SQL query (20+ transaction types).
Columns: shopid, itemid, itemname, packingtype, sdate, transno, transid,
         qty, type, mode, updatetime, costprice, depcostprice, concostprice, from_to, extra
mode=1 stock IN, mode=-1 stock OUT.
"""

SQL_STOCK_MOVEMENT = """
SELECT * FROM (
-- Goods Return
SELECT grn.grnhShopid AS shopid, grd.GRNDItemID AS itemid,
  ISNULL(Itm.ItemDescription,'') AS itemname, ISNULL(ptn.PackingTypeName,'') AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),GrnhGoodsreturnnoteDate,111)) AS sdate,
  GrnhGoodsreturnnoteNO AS transno, GrnhGoodsreturnnoteID AS transid,
  CONVERT(NUMERIC(18,8),ISNULL(GRNDQuantity,0)) AS qty,
  'Goods Return' AS type, 1 AS mode, grn.updatetime,
  grncostprice AS costprice, grncostprice*grnhdepexrate AS depcostprice,
  grncostprice*grnhExchangeRate AS concostprice, '' AS from_to, '' AS extra
FROM LosGoodsReturnNoteHeader grn
INNER JOIN LosGoodsReturnNoteDetail grd ON grn.GrnhGoodsreturnnoteID=grd.GRNDReturnNoteID AND grn.grnhShopid=grd.GRNDShopid
INNER JOIN aItem Itm ON Itm.ItemID=grd.GRNDItemID
INNER JOIN aPackingTypeCapacityDetail PkType ON grd.grndPackTypeId=PkType.PackingTypeID AND Itm.UnitsID=PkType.UnitsID
LEFT JOIN aPackingType ptn ON ptn.PackingTypeID=grd.grndPackTypeId
WHERE GrnhCancel=0 AND GRNDDamaged=0

UNION ALL
-- Transfer In
SELECT h.tihshopid, d.tiditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, ISNULL(ptn.PackingTypeName,'') AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),h.tihdate,111)) AS sdate,
  h.tihno, h.tihid, CONVERT(NUMERIC(18,8),SUM(d.TIDrecievedgoodqty)) AS qty,
  'Transfer In' AS type, 1 AS mode, h.updatetime,
  tidCostPrice, tidCostPrice*tihdepexrate, tidCostPrice*tihconexrate,
  s.ShopName AS from_to, '' AS extra
FROM lostransferinheader h
LEFT JOIN aShops s ON s.ShopID=h.TIHfromshopID
INNER JOIN lostransferindetail d ON h.tihid=d.tidid AND h.tihshopid=d.tidshopid
LEFT JOIN aItem itm ON itm.ItemID=d.tiditemid
LEFT JOIN aPackingType ptn ON ptn.PackingTypeID=d.tidPackingTypeID
WHERE h.tihcancel=0 AND h.tihtransfinished=1
GROUP BY h.tihshopid,h.tihdate,h.tihid,h.tihno,d.tiditemid,h.updatetime,
  tidCostPrice,tihdepexrate,tihconexrate,s.ShopName,itm.ItemDescription,ptn.PackingTypeName

UNION ALL
-- Recovery Plus
SELECT sr.srshopid, sr.sritemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  sr.srdate,
  'Rec'+CONVERT(VARCHAR(50),sr.srid), sr.srid,
  CONVERT(NUMERIC(18,8),ISNULL(SUM(sr.sraddstock),0)) AS qty,
  'Recovery Plus' AS type, 1 AS mode, sr.updatetime,
  srCostPrice, srcostprice*srdepexrate, srcostprice*srconexrate, '', ''
FROM losstockrecovery sr
LEFT JOIN aItem itm ON itm.ItemID=sr.sritemid
GROUP BY sr.srshopid,sr.srdate,sr.srid,sr.sritemid,sr.updatetime,srCostPrice,srdepexrate,srconexrate,itm.ItemDescription
HAVING ISNULL(SUM(sr.sraddstock),0)>0

UNION ALL
-- Verification Plus
SELECT svdshopid, svdItemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),svhDate,111)) AS sdate,
  svhno, svhid,
  CONVERT(NUMERIC(18,8),SUM(svdVerifiedStock-svdAvailStock)) AS qty,
  'Verification Plus' AS type, 1 AS mode, sv.updatetime,
  svdCostPrice, svdCostPrice*svhdepexrate, svdCostPrice*svhconexrate, '', ''
FROM losstockverificationheader sv
INNER JOIN losstockverificationdetail ON svhid=svdid AND svhshopid=svdshopid
LEFT JOIN aItem itm ON itm.ItemID=svdItemid
WHERE svdVerifiedStock>svdAvailStock AND svhCancelled=0 AND LEFT(svhFutureVc,1)<>'t'
GROUP BY svdShopID,svhdate,svhid,svhno,svdItemid,sv.updatetime,svdCostPrice,svhdepexrate,svhconexrate,itm.ItemDescription

UNION ALL
-- Total Verification Plus
SELECT svdshopid, svdItemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),svhDate,111)) AS sdate,
  svhno, svhid,
  CONVERT(NUMERIC(18,8),SUM(svdVerifiedStock-svdAvailStock)) AS qty,
  'Verification Plus' AS type, 1 AS mode, sv.updatetime,
  svdCostPrice, svdCostPrice*svhdepexrate, svdCostPrice*svhconexrate, '', ''
FROM losstockverificationheader sv
INNER JOIN losstockverificationdetail ON svhid=svdid AND svhshopid=svdshopid
LEFT JOIN aItem itm ON itm.ItemID=svdItemid
WHERE svdVerifiedStock>svdAvailStock AND svhCancelled=0 AND LEFT(svhFutureVc,2)='tc'
GROUP BY svdShopID,svhdate,svhid,svhno,svdItemid,sv.updatetime,svdCostPrice,svhdepexrate,svhconexrate,itm.ItemDescription

UNION ALL
-- Exchange In
SELECT sehShopID, seditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),sehExchangeDate,111)) AS sdate,
  sehexchangeno, sehexchangeid,
  CONVERT(NUMERIC(18,8),SUM(ISNULL(sedExchangeQty,0))) AS qty,
  'Exchanged In' AS type, 1 AS mode, eh.updatetime,
  sedCostPrice, sedCostPrice*sehdepexrate, sedCostPrice*sehExchangerate, '', ''
FROM losposexchangeheader eh
INNER JOIN losposexchangedetail ON sedExchangeid=sehExchangeID AND sedShopID=sehShopid
LEFT JOIN aItem itm ON itm.ItemID=seditemid
WHERE sedBillorExchange='B' AND SEHCANCELLED=0 AND ISNULL(sedExchangeQty,0)>0
GROUP BY sehShopID,sehExchangeDate,sehexchangeid,sehexchangeno,seditemid,eh.updatetime,
  sedCostPrice,sehDepExrate,sehExchangerate,itm.ItemDescription

UNION ALL
-- Local Purchase (costed)
SELECT lphShopid, lpditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, ISNULL(ptn.PackingTypeName,'') AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),lphbilldate,111)) AS sdate,
  lphBillNo, lphBillid,
  CONVERT(NUMERIC(18,8),SUM(ISNULL(lpdItemQuantity,0))) AS qty,
  'Local Purchase' AS type, 1 AS mode, lo.updatetime,
  d.lpcdnewitemcostprice, d.lpcdnewitemcostprice, d.lpcdnewitemcostprice,
  '' AS from_to, ISNULL(v.VendorName,'') AS extra
FROM loslocalpurchasedetail ld
INNER JOIN loslocalpurchaseheader lo ON lphBillId=lpdBillID AND lphShopID=lpdShopid AND lphCancelled=0 AND lphConfirmed=1
INNER JOIN loalocalpurchaseCostingheader h ON lpchBillid=lphBillid AND lpchShopid=lphShopid AND lpchCancelled=0
INNER JOIN loalocalpurchaseCostingdetail d ON h.lpchcostingid=d.lpcdcostingid AND lpchCancelled=0 AND d.lpcditemid=ld.lpditemid
LEFT JOIN avendormaster v ON v.VendorID=lo.lphVendorID
LEFT JOIN aItem itm ON itm.ItemID=lpditemid
LEFT JOIN aPackingType ptn ON ptn.PackingTypeID=CAST(ld.lpdpackid AS INT)
GROUP BY lphshopid,lphBillid,lphBillNo,lphbilldate,lpditemid,lo.updatetime,
  lpdItemUnitPrice,lpdItemQuantity,lphdepexrate,lphExchangerate,d.lpcdnewitemcostprice,v.VendorName,
  itm.ItemDescription,ptn.PackingTypeName

UNION ALL
-- Local Purchase (uncosted, zero cost)
SELECT lphShopid, lpditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, ISNULL(ptn.PackingTypeName,'') AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),lphbilldate,111)) AS sdate,
  lphBillNo, lphBillid,
  CONVERT(NUMERIC(18,8),SUM(ISNULL(lpdItemQuantity,0))) AS qty,
  'Local Purchase' AS type, 1 AS mode, lo.updatetime,
  0, 0, 0, '' AS from_to, ISNULL(v.VendorName,'') AS extra
FROM loslocalpurchasedetail ld
INNER JOIN loslocalpurchaseheader lo ON lphBillId=lpdBillID AND lphShopID=lpdShopid AND lphCancelled=0 AND lphConfirmed=1
LEFT JOIN avendormaster v ON v.VendorID=lo.lphVendorID
LEFT JOIN aItem itm ON itm.ItemID=lpditemid
LEFT JOIN aPackingType ptn ON ptn.PackingTypeID=CAST(ld.lpdpackid AS INT)
WHERE ISNULL(lpdPOUnitPrice,0)=0
  AND lphBillid NOT IN (SELECT lpchBillid FROM loalocalpurchaseCostingheader h WHERE h.lpchCancelled=0)
GROUP BY lphshopid,lphBillid,lphBillNo,lphbilldate,lpditemid,lo.updatetime,
  lpdItemUnitPrice,lpdItemQuantity,lphdepexrate,lphExchangerate,v.VendorName,
  itm.ItemDescription,ptn.PackingTypeName

UNION ALL
-- In-House Return
SELECT IHRHShopID, IHRDItemID,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),IHRHDate,111)) AS sdate,
  IHRHNo, IHRHID,
  CONVERT(NUMERIC(18,8),SUM(IHRDReturnedqty)) AS qty,
  'In-House Return' AS type, 1 AS mode, rh.updatetime,
  IHRDcostprice, IHRHdepexrate*IHRDcostprice, IHRHconexrate*IHRDcostprice, '', ''
FROM LOs_InHouseCons_ReturnHeader rh
INNER JOIN LOs_InHouseCons_ReturnDetail rd ON IHRHShopID=IHRDShopID AND IHRHID=IHRDID
LEFT JOIN aItem itm ON itm.ItemID=IHRDItemID
WHERE IHRHCancelled=0 AND IHRHConfirmed=1
  AND (IHRDRetrnOrExch='R' OR IHRDRetrnOrExch='B' OR IHRDRetrnOrExch IS NULL) AND IHRDReturnedqty<>0
GROUP BY IHRHShopID,IHRDItemID,IHRHDate,IHRHNo,IHRHID,rh.updatetime,IHRDcostprice,IHRHdepexrate,IHRHconexrate,itm.ItemDescription

UNION ALL
-- Merging Add
SELECT lsdShopID, lshItemID,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  lshDate, lshno, lshid,
  CONVERT(NUMERIC(18,8),SUM(lsdqty)) AS qty,
  'Merging Add' AS type, 1 AS mode, lshUpdatetime, NULL, NULL, NULL, '', ''
FROM losMergeDetails md
INNER JOIN losMergeHeader mh ON md.lsdid=mh.lshid AND md.lsdShopID=mh.lshShopid
LEFT JOIN aItem itm ON itm.ItemID=lshItemID
WHERE lshCancelled=0
GROUP BY lsdShopID,lshItemID,lshDate,lshid,lshno,lshUpdatetime,itm.ItemDescription
HAVING SUM(lsdQty)<>0

UNION ALL
-- === STOCK OUT (mode = -1) ===
-- Write Off
SELECT wh.whshopid, wd.wditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),whdate,111)) AS sdate,
  wh.whno, wh.whid,
  CONVERT(NUMERIC(18,8),SUM(wd.wdWriteoffQty)) AS qty,
  'Write Off' AS type, -1 AS mode, wh.updatetime,
  wdCostPrice, wdCostPrice*whdepexrate, wdCostPrice*whConExrate, '', ''
FROM loswriteoffheader wh
INNER JOIN loswriteoffdetail wd ON wh.whid=wd.wdid AND wh.whshopid=wd.wdshopid
LEFT JOIN aItem itm ON itm.ItemID=wd.wditemid
WHERE wh.whcancelled=0 AND whtype<>'I'
GROUP BY wh.whshopid,wh.whDate,wh.whid,wh.whno,wd.wditemid,wh.updatetime,wdCostPrice,whDepExrate,whConExrate,itm.ItemDescription

UNION ALL
-- In-House Consumption
SELECT wh.whshopid, wd.wditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),wh.whdate,111)) AS sdate,
  wh.whno, wh.whid,
  CONVERT(NUMERIC(18,8),SUM(wd.wdWriteoffQty)) AS qty,
  'In-House Cons' AS type, -1 AS mode, wh.updatetime,
  wdCostPrice, wdCostPrice*whdepexrate, wdCostPrice*whConExrate, '', ''
FROM loswriteoffheader wh
INNER JOIN loswriteoffdetail wd ON wh.whid=wd.wdid AND wh.whshopid=wd.wdshopid
LEFT JOIN aItem itm ON itm.ItemID=wd.wditemid
WHERE wh.whcancelled=0 AND whtype='I' AND whVerified=1
GROUP BY wh.whshopid,wh.whDate,wh.whid,wh.whno,wd.wditemid,wh.updatetime,wdCostPrice,whDepExrate,whConExrate,itm.ItemDescription

UNION ALL
-- Despatch To Godown
SELECT dd.dgdshopid, dd.dgditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  dh.dghDate,
  dh.dghNo, dh.dghid,
  CONVERT(NUMERIC(18,8),SUM(dd.dgddespatchedgoodqty)) AS qty,
  'Despatch To Godown' AS type, -1 AS mode, dh.updatetime,
  dgdCostPrice, dgdCostPrice*dghdepexrate, dgdCostPrice*dghConExrate,
  g.GodownName AS from_to, '' AS extra
FROM mesdespatchtogodownheader dh
LEFT JOIN aGodown g ON g.GodownID=dh.dghGodownID
INNER JOIN mesdespatchtogodowndetail dd ON dh.dghid=dd.dgdid AND dh.dghshopid=dd.dgdshopid
LEFT JOIN aItem itm ON itm.ItemID=dd.dgditemid
WHERE dh.dghcancelled=0 AND dghtransfinished=1
GROUP BY dd.dgdshopid,dh.dghdate,dh.dghid,dh.dghNo,dd.dgditemid,dh.updatetime,
  dgdCostPrice,dghdepexrate,dghconexrate,g.GodownName,itm.ItemDescription

UNION ALL
-- Transfer Out
SELECT todshopid, toditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),h.tohdate,111)) AS sdate,
  tohno, tohid,
  CONVERT(NUMERIC(18,8),SUM(todissuedgoodqty)) AS qty,
  'Transfer Out' AS type, -1 AS mode, h.updatetime,
  todCostPrice, todCostPrice*tohdepexrate, todCostPrice*tohConExrate,
  s.ShopName AS from_to, '' AS extra
FROM mestransferoutdetail
INNER JOIN mestransferoutheader h ON tohid=todid AND Tohshopid=todshopid AND tohcancelled=0 AND tohtransfinished=1
INNER JOIN aShops s ON s.ShopID=h.TOHtoShopid
LEFT JOIN aItem itm ON itm.ItemID=toditemid
GROUP BY todissuedgoodqty,tohid,todshopid,tohdate,tohid,tohno,todItemid,h.updatetime,
  todCostPrice,tohdepexrate,tohConExrate,s.ShopName,itm.ItemDescription

UNION ALL
-- Recovery Minus
SELECT sr.srshopid, sr.sritemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  sr.srdate,
  'Rec'+CONVERT(VARCHAR(50),sr.srid), sr.srid,
  CONVERT(NUMERIC(18,8),SUM(ISNULL(sr.srdedstock,0))) AS qty,
  'Recovery Minus' AS type, -1 AS mode, sr.updatetime,
  srCostPrice, srcostprice*srdepexrate, srcostprice*srconexrate, '', ''
FROM losstockrecovery sr
LEFT JOIN aItem itm ON itm.ItemID=sr.sritemid
GROUP BY sr.srshopid,sr.srdate,sr.srid,sr.sritemid,sr.updatetime,srCostPrice,srdepexrate,srconexrate,itm.ItemDescription
HAVING SUM(ISNULL(sr.srdedstock,0))>0

UNION ALL
-- Verification Minus
SELECT svdshopid, svdItemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),svhDate,111)) AS sdate,
  svhno, svhid,
  CONVERT(NUMERIC(18,8),SUM(svdAvailStock-svdVerifiedStock)) AS qty,
  'Verification Minus' AS type, -1 AS mode, sv.updatetime,
  svdCostPrice, svdCostPrice*svhdepexrate, svdCostPrice*svhconexrate, '', ''
FROM losstockverificationheader sv
INNER JOIN losstockverificationdetail ON svhid=svdid AND svhshopid=svdshopid
LEFT JOIN aItem itm ON itm.ItemID=svdItemid
WHERE svdVerifiedStock<svdAvailStock AND svhCancelled=0 AND LEFT(svhFutureVc,1)<>'t'
GROUP BY svdShopID,svhdate,svhid,svhno,svdItemid,sv.updatetime,svdCostPrice,svhdepexrate,svhconexrate,itm.ItemDescription

UNION ALL
-- Total Verification Minus
SELECT svdshopid, svdItemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),svhDate,111)) AS sdate,
  svhno, svhid,
  CONVERT(NUMERIC(18,8),SUM(svdAvailStock-svdVerifiedStock)) AS qty,
  'Verification Minus' AS type, -1 AS mode, sv.updatetime,
  svdCostPrice, svdCostPrice*svhdepexrate, svdCostPrice*svhconexrate, '', ''
FROM losstockverificationheader sv
INNER JOIN losstockverificationdetail ON svhid=svdid AND svhshopid=svdshopid
LEFT JOIN aItem itm ON itm.ItemID=svdItemid
WHERE svdVerifiedStock<svdAvailStock AND svhCancelled=0 AND LEFT(svhFutureVc,2)='tc'
GROUP BY svdShopID,svhdate,svhid,svhno,svdItemid,sv.updatetime,svdCostPrice,svhdepexrate,svhconexrate,itm.ItemDescription

UNION ALL
-- POS Cash Sales (product items, itemtype='P')
SELECT poshShopID, posditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, ISNULL(ptn.PackingTypeName,'') AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),poshBilldate,111)) AS sdate,
  poshBillNo, poshbillid,
  CONVERT(NUMERIC(18,8),SUM(ISNULL(posdquantity,0))) AS qty,
  'Cash Sales' AS type, -1 AS mode, ph.updatetime,
  posdCostPrice, posdCostPrice*poshdepexrate, posdCostPrice*poshExchangeRate,
  '' AS from_to,
  CASE WHEN ISNULL(poshCustomerName,'')='' THEN 'CASH' ELSE poshCustomerName END AS extra
FROM LOsPosDetail pd2
INNER JOIN LOsPosHeader ph ON poshBillid=pd2.posdBillid AND poshShopid=pd2.posdshopid
INNER JOIN aItem itm ON itm.Itemid=pd2.posdItemID AND itm.itemtype='P'
LEFT JOIN aPackingType ptn ON ptn.PackingTypeID=pd2.posdPackingTypeID
WHERE POSHCANCELLED=0
GROUP BY poshShopid,poshbillid,poshBillNo,poshbilldate,
  pd2.posditemid,ph.updatetime,posdCostPrice,poshdepexrate,poshExchangeRate,poshCustomerName,
  itm.ItemDescription,ptn.PackingTypeName

UNION ALL
-- F&B Sales (order ingredients, menu itemtype='f')
SELECT ph.poshShopID, il.ItemID,
  ISNULL(im.ItemDescription,'') AS itemname, ISNULL(ptn.PackingTypeName,'') AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),ph.poshBilldate,111)) AS sdate,
  ph.poshBillNo+'(order/'+CAST(oh.OrderID AS VARCHAR)+')' AS transno,
  ph.poshBillid AS transid,
  CONVERT(NUMERIC(18,3),il.Qty) AS qty,
  'F and B Sales' AS type, -1 AS mode, ph.updatetime,
  ISNULL(il.CostingValue,0) AS costprice,
  ISNULL(il.CostingValue,0)*ph.poshdepexrate AS depcostprice,
  ISNULL(il.CostingValue,0)*ph.poshExchangeRate AS concostprice,
  '' AS from_to,
  ISNULL(poshCustomerName,'CASH') AS extra
FROM LOsPosDetail pd
INNER JOIN LOsPosHeader ph ON ph.poshBillid=pd.posdBillid AND ph.poshShopid=pd.posdShopid
INNER JOIN OrderHeader oh ON oh.BillID=ph.poshBillid AND oh.ShopID=ph.poshShopID
LEFT JOIN IngredientDetails il ON pd.posditemid=il.MenuItemID AND il.billid=ph.poshBillid
LEFT JOIN aItem im ON il.ItemID=im.ItemID
LEFT JOIN aPackingType ptn ON ptn.PackingTypeID=il.PackingTypeID
WHERE ph.POSHCANCELLED=0 AND pd.posdItemType='f' AND il.Qty>0

UNION ALL
-- Credit Invoice
SELECT IhShopid, iditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),ihInvoicedate,111)) AS sdate,
  ihInvoiceNo, ihInvoiceid,
  CONVERT(NUMERIC(18,8),SUM(ISNULL(idquantity,0))) AS qty,
  'Credit Sales' AS type, -1 AS mode, ih.updatetime,
  idCostPrice, idCostPrice*ihdepexrate, idCostPrice*ihExchangeRate, '', ''
FROM losinvoicedetail id2
INNER JOIN losinvoiceheader ih ON ihInvoiceid=id2.idInvoiceid AND ihshopid=id2.idshopid
LEFT JOIN aItem itm ON itm.ItemID=id2.iditemid
WHERE IHCANCELLED=0 AND ihproforma=0 AND ihType='I'
GROUP BY ihshopid,ihinvoicedate,ihInvoiceid,ihInvoiceNo,id2.iditemid,ih.updatetime,
  idCostPrice,ihdepexrate,ihExchangeRate,itm.ItemDescription

UNION ALL
-- Exchange Out
SELECT sehShopID, seditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),sehExchangeDate,111)) AS sdate,
  sehexchangeno, sehexchangeid,
  CONVERT(NUMERIC(18,8),SUM(ISNULL(sedquantity,0))) AS qty,
  'Exchange Out' AS type, -1 AS mode, eh.updatetime,
  sedCostPRice, sedCostPrice*sehdepexrate, sedCostPrice*sehExchangerate, '', ''
FROM losposexchangeheader eh
INNER JOIN losposexchangedetail ON sedExchangeid=sehExchangeID AND sedShopID=sehShopid
LEFT JOIN aItem itm ON itm.ItemID=seditemid
WHERE sedBillorExchange='E' AND SEHCANCELLED=0
GROUP BY sehShopID,sehExchangeDate,sehexchangeid,sehexchangeno,seditemid,eh.updatetime,
  sedCostPRice,sehdepexrate,sehExchangerate,itm.ItemDescription

UNION ALL
-- Purchase Return
SELECT Ph.whshopid, Pd.wditemid,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),Ph.whdate,111)) AS sdate,
  Ph.whno, Ph.whid,
  CONVERT(NUMERIC(18,8),SUM(Pd.wdPurchaseReturnQty)) AS qty,
  'Purchase Return' AS type, -1 AS mode, Ph.updatetime,
  wdCostPrice, wdCostPrice*whdepexrate, wdCostPrice*whConExrate, '', ''
FROM losPurchaseReturnheader Ph
INNER JOIN losPurchaseReturndetail Pd ON Ph.whid=Pd.wdid AND Ph.whshopid=Pd.wdshopid
LEFT JOIN aItem itm ON itm.ItemID=Pd.wditemid
WHERE Ph.whcancelled=0 AND Ph.whtransfinished=1
GROUP BY Ph.whshopid,Ph.whDate,Ph.whid,Ph.whno,Pd.wditemid,Ph.updatetime,wdCostPrice,whDepExrate,whConExrate,itm.ItemDescription

UNION ALL
-- Merging Deduct
SELECT lsdShopID, lsdItemID,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  lshDate, lshno, lshid,
  CONVERT(NUMERIC(18,8),SUM(lsdqty)) AS qty,
  'Merging Deduct' AS type, -1 AS mode, lshUpdatetime, NULL, NULL, NULL, '', ''
FROM losMergeDetails md
INNER JOIN losMergeHeader mh ON md.lsdid=mh.lshid AND md.lsdShopid=mh.lshShopId
LEFT JOIN aItem itm ON itm.ItemID=lsdItemID
WHERE lshCancelled=0
GROUP BY lsdShopID,lsdItemID,lshDate,lshid,lshno,lshUpdatetime,itm.ItemDescription
HAVING SUM(lsdQty)<>0

UNION ALL
-- In-House Exchanged In (stock out from source)
SELECT IHRHShopID, IHRDItemID,
  ISNULL(itm.ItemDescription,'') AS itemname, '' AS packingtype,
  CONVERT(DATETIME,CONVERT(VARCHAR(10),IHRHDate,111)) AS sdate,
  IHRHNo, IHRHID,
  CONVERT(NUMERIC(18,8),SUM(IHRDArrivedQty)) AS qty,
  'In-House Exchanged In' AS type, -1 AS mode, rh.updatetime,
  IHRDcostprice, IHRHdepexrate*IHRDcostprice, IHRHconexrate*IHRDcostprice, '', ''
FROM LOs_InHouseCons_ReturnHeader rh
INNER JOIN LOs_InHouseCons_ReturnDetail rd ON IHRHShopID=IHRDShopID AND IHRHID=IHRDID
LEFT JOIN aItem itm ON itm.ItemID=IHRDItemID
WHERE IHRHCancelled=0 AND IHRHConfirmed=1 AND IHRDRetrnOrExch='E' AND IHRDArrivedQty<>0
GROUP BY IHRHShopID,IHRDItemID,IHRHDate,IHRHNo,IHRHID,rh.updatetime,IHRDcostprice,IHRHdepexrate,IHRHconexrate,itm.ItemDescription
) stk
WHERE stk.shopid IN (SELECT ShopID FROM aShops WHERE futurevarchar = 'f')
"""

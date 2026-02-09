"""
Authentication and company access service.

Auth DB tables (expected):
- dbo.UserAuthentication (EmailId/emailid, Password/password, UserId/userid)
- dbo.UserPrintCompany (UserId, CompanyId, AllowPreset, AllowTemplate, AllowPreview, AllowTemplateConfig, IsActive)
- dbo.CompanyProfile (CompanyID, CompanyName, DBname, DBserver, DBuserName, DBpassword)
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any, Optional, List, Dict

from db import database as db


class AuthService:
    def _sha1_bytes_email_password(self, email: str, password: str) -> bytes:
        """
        Match .NET:
          SHA1(Encoding.Unicode.GetBytes(UserID + Password))

        In .NET, Encoding.Unicode is UTF-16LE.
        """
        joined = f"{email}{password}"
        return hashlib.sha1(joined.encode("utf-16le")).digest()

    def _normalize_db_hash_bytes(self, value: Any) -> bytes:
        """
        Normalize password values coming from SQL Server into raw bytes.
        Supports:
        - bytes (VARBINARY)
        - strings like '0xABCD...'
        - plain hex strings
        """
        if value is None:
            return b""
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        s = str(value).strip()
        if s.lower().startswith("0x"):
            s = s[2:]
        s = s.strip()
        try:
            return bytes.fromhex(s)
        except ValueError:
            return b""

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate against dbo.UserAuthentication.
        Returns dict with at least {user_id, email} on success, else None.
        Always uses auth DB for authentication queries.
        """
        q = """
            SELECT TOP 1 *
            FROM [dbo].[UserAuthentication]
            WHERE [emailid] = @email
        """
        rows = db.execute_query(q, {"email": email}, use_auth_db=True)
        if not rows:
            return None

        row = rows[0]
        # Try common column names for password
        stored_pw = None
        for k in ("password", "Password", "PASSWORD"):
            if k in row:
                stored_pw = row[k]
                break
        if stored_pw is None:
            return None

        stored_bytes = self._normalize_db_hash_bytes(stored_pw)
        provided_bytes = self._sha1_bytes_email_password(email.strip(), password)

        if not stored_bytes or len(stored_bytes) != len(provided_bytes):
            return None
        if not hmac.compare_digest(stored_bytes, provided_bytes):
            return None

        user_id: Optional[int] = None
        for k in ("UserId", "userid", "UserID", "Id", "ID"):
            if k in row:
                user_id = int(row[k])
                break
        if user_id is None:
            return None

        return {"user_id": user_id, "email": email}

    def get_user_companies(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Return companies mapped to a user, with permissions, filtered to active mappings.
        Always queries the auth database.
        """
        q = """
            SELECT
                upc.CompanyId,
                cp.CompanyName,
                cp.PermanentAddress,
                cp.CompanyDescription,
                cp.PhoneNo,
                upc.AllowPreset,
                upc.AllowTemplate,
                upc.AllowPreview,
                upc.AllowTemplateConfig
            FROM dbo.UserPrintCompany upc
            LEFT JOIN dbo.CompanyProfile cp ON cp.CompanyID = upc.CompanyId
            WHERE upc.UserId = @user_id
              AND upc.IsActive = 1
        """
        return db.execute_query(q, {"user_id": user_id}, use_auth_db=True)

    def get_company_details(self, company_id: int) -> Optional[Dict[str, Any]]:
        """
        Get DB connection details for a company from auth DB.
        Always queries the auth database.
        """
        q = """
            SELECT TOP 1
                CompanyID,
                CompanyName,
                DBname,
                DBserver,
                DBuserName,
                DBpassword
            FROM dbo.CompanyProfile
            WHERE CompanyID = @company_id
        """
        rows = db.execute_query(q, {"company_id": company_id}, use_auth_db=True)
        return rows[0] if rows else None


auth_service = AuthService()


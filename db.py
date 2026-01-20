import pyodbc

def get_connection(
    server="TEST-DB",
    database="dbAAFS_MAFS",
    user= "jaccsadmin",
    password="J@ccs@admin",
    driver="{ODBC Driver 17 for SQL Server}",
    # encrypt="yes",
    # trustservercertificate="yes",

    # local
    # server="localhost,1433",
    # database="scoringDB",
    # user="sa",
    # password="MyStrongPass123",
    # driver="{ODBC Driver 18 for SQL Server}",
):
    conn_str = (
        f"DRIVER={driver};SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        # f"Encrypt={encrypt};TrustServerCertificate={trustservercertificate};"
    )
    return pyodbc.connect(conn_str)

def fetch_ci_mock_crifv4(party_no: int, application_no: int, conn=None):
    """
    Calls: EXEC dbo.CIMockCrifv4 @party=?, @application=?
    Returns: a single row as {column: value} or None if nothing.
    """
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            cur.execute("EXEC dbo.CIMockCrifv4 @party = ?, @application = ?", party_no, application_no)
            columns = [c[0] for c in cur.description] if cur.description else []
            row = cur.fetchone()
            if not row:
                return None
            data = dict(zip(columns, row))
            return data
    finally:
        if close_conn:
            conn.close()

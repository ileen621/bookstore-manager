import sqlite3
from typing import Tuple, Optional
import re

DB_NAME = 'bookstore.db'


def connect_db() -> sqlite3.Connection:
    """
    建立並返回 SQLite 資料庫連線，使用 Row 作為 row_factory。
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db(conn: sqlite3.Connection) -> None:
    """
    初始化資料表並插入預設資料（若尚未存在）。
    """
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS member (
            mid TEXT PRIMARY KEY,
            mname TEXT NOT NULL,
            mphone TEXT NOT NULL,
            memail TEXT
        );
        CREATE TABLE IF NOT EXISTS book (
            bid TEXT PRIMARY KEY,
            btitle TEXT NOT NULL,
            bprice INTEGER NOT NULL,
            bstock INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sale (
            sid INTEGER PRIMARY KEY AUTOINCREMENT,
            sdate TEXT NOT NULL,
            mid TEXT NOT NULL,
            bid TEXT NOT NULL,
            sqty INTEGER NOT NULL,
            sdiscount INTEGER NOT NULL,
            stotal INTEGER NOT NULL
        );
    """ )
    # 插入 member
    cursor.execute("SELECT COUNT(*) FROM member")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
            INSERT INTO member VALUES ('M001','Alice','0912-345678','alice@example.com');
            INSERT INTO member VALUES ('M002','Bob','0923-456789','bob@example.com');
            INSERT INTO member VALUES ('M003','Cathy','0934-567890','cathy@example.com');
        """ )
    # 插入 book
    cursor.execute("SELECT COUNT(*) FROM book")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
            INSERT INTO book VALUES ('B001','Python Programming',600,50);
            INSERT INTO book VALUES ('B002','Data Science Basics',800,30);
            INSERT INTO book VALUES ('B003','Machine Learning Guide',1200,20);
        """ )
    # 插入 sale
    cursor.execute("SELECT COUNT(*) FROM sale")
    if cursor.fetchone()[0] == 0:
        cursor.executescript("""
            INSERT INTO sale(sdate,mid,bid,sqty,sdiscount,stotal) VALUES
                ('2024-01-15','M001','B001',2,100,1100),
                ('2024-01-16','M002','B002',1,50,750),
                ('2024-01-17','M001','B003',1,0,1200),
                ('2024-01-18','M003','B001',1,0,600),
                ('2024-01-19','M002','B003',2,150,2250);
        """ )
    conn.commit()


def is_valid_date(date_str: str) -> bool:
    """
    驗證日期格式為 YYYY-MM-DD。
    """
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str))


def get_valid_integer_input(prompt: str) -> Optional[int]:
    """
    輸入整數或空，空返回 None。
    """
    while True:
        s = input(prompt)
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            print("=> 錯誤：請輸入有效的整數")


def get_valid_positive_integer_input(prompt: str) -> Optional[int]:
    """
    輸入正整數或空。
    """
    while True:
        v = get_valid_integer_input(prompt)
        if v is None or v > 0:
            return v
        print("=> 錯誤：數量必須為正整數")


def get_valid_non_negative_integer_input(prompt: str) -> Optional[int]:
    """
    輸入非負整數或空。
    """
    while True:
        v = get_valid_integer_input(prompt)
        if v is None or v >= 0:
            return v
        print("=> 錯誤：折扣金額不能為負數")


def add_sale(conn: sqlite3.Connection, sdate: str, mid: str, bid: str, sqty: int, sdiscount: int) -> Tuple[bool, str]:
    """
    新增銷售，檢查會員/書籍編號及庫存，計算並更新。
    返回 (True, 訊息) 或 (False, 錯誤)
    """
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM member WHERE mid=?", (mid,))
        ok1 = cur.fetchone()
        cur.execute("SELECT bprice,bstock FROM book WHERE bid=?", (bid,))
        b = cur.fetchone()
        if not ok1 or not b:
            return False, "錯誤：會員編號或書籍編號無效"
        if b['bstock'] < sqty:
            return False, f"錯誤：書籍庫存不足 (剩餘 {b['bstock']})"
        total = b['bprice'] * sqty - sdiscount
        cur.execute(
            "INSERT INTO sale(sdate,mid,bid,sqty,sdiscount,stotal) VALUES(?,?,?,?,?,?)",
            (sdate, mid, bid, sqty, sdiscount, total)
        )
        cur.execute("UPDATE book SET bstock=bstock-? WHERE bid=?", (sqty, bid))
        conn.commit()
        return True, f"銷售記錄已新增！(銷售總額: {total:,})"
    except sqlite3.Error:
        conn.rollback()
        return False, "=> 發生資料庫操作錯誤"


def add_new_sale(conn: sqlite3.Connection) -> None:
    sdate = input("請輸入銷售日期 (YYYY-MM-DD)：")
    if not is_valid_date(sdate):
        print("=> 錯誤：日期格式錯誤")
        return
    mid = input("請輸入會員編號：")
    bid = input("請輸入書籍編號：")
    sqty = get_valid_positive_integer_input("請輸入購買數量：")
    if sqty is None:
        return
    sdiscount = get_valid_non_negative_integer_input("請輸入折扣金額：")
    if sdiscount is None:
        return
    ok, msg = add_sale(conn, sdate, mid, bid, sqty, sdiscount)
    print(f"=> {msg}")


def print_sale_report(conn: sqlite3.Connection) -> None:
    """
    顯示所有銷售報表。
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice, s.sqty, s.sdiscount, s.stotal
        FROM sale s
        JOIN member m ON s.mid = m.mid
        JOIN book b ON s.bid = b.bid
        ORDER BY s.sid
    """
    )
    sales = cur.fetchall()

    print("========================= 銷售報表 ==========================")
    for sale in sales:
        print(f"銷售 #{sale['sid']}")
        print(f"銷售編號: {sale['sid']}")
        print(f"銷售日期: {sale['sdate']}")
        print(f"會員姓名: {sale['mname']}")
        print(f"書籍標題: {sale['btitle']}")
        print("--------------------------------------------------")
        print(f"{'單價':<10}{'數量':<8}{'折扣':<8}{'小計':<8}")
        print("--------------------------------------------------")
        print(f"{sale['bprice']:<12,}{sale['sqty']:<10}{sale['sdiscount']:<10,}{sale['stotal']:<10,}")
        print("--------------------------------------------------")
        print(f"銷售總額: {sale['stotal']:,}")
        print("==================================================\n")


def update_sale_record(conn: sqlite3.Connection) -> None:
    """
    更新指定銷售紀錄的折扣金額，並重新計算總額。
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT s.sid, m.mname, s.sdate FROM sale s JOIN member m ON s.mid=m.mid ORDER BY s.sid"
    )
    sales = cur.fetchall()
    if not sales:
        print("=> 沒有任何銷售紀錄可供更新。")
        return
    print("\n======== 銷售紀錄列表 ========")
    for i, rec in enumerate(sales, start=1):
        print(f"{i}. 銷售編號: {rec['sid']} - 會員: {rec['mname']} - 日期: {rec['sdate']}")
    print("===============================" )
    choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ").strip()
    if not choice:
        return
    try:
        idx = int(choice)
        if idx < 1 or idx > len(sales):
            raise ValueError
    except ValueError:
        print("=> 錯誤：請輸入有效的數字")
        return
    sid = sales[idx-1]['sid']
    cur.execute("SELECT * FROM sale WHERE sid=?", (sid,))
    sale = cur.fetchone()
    new_discount = get_valid_non_negative_integer_input("請輸入新的折扣金額：")
    if new_discount is None:
        return
    cur.execute("SELECT bprice FROM book WHERE bid=?", (sale['bid'],))
    price = cur.fetchone()['bprice']
    new_total = price * sale['sqty'] - new_discount
    try:
        cur.execute("UPDATE sale SET sdiscount=?, stotal=? WHERE sid=?", (new_discount, new_total, sid))
        conn.commit()
        print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {new_total:,})")
    except sqlite3.Error:
        conn.rollback()
        print("=> 更新失敗，請稍後再試。")


def delete_sale_record(conn: sqlite3.Connection) -> None:
    """
    刪除指定的銷售記錄。
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT s.sid, m.mname, s.sdate FROM sale s JOIN member m ON s.mid=m.mid ORDER BY s.sid"
    )
    sales = cur.fetchall()
    if not sales:
        print("=> 沒有任何銷售紀錄可供刪除。")
        return
    print("\n======== 銷售紀錄列表 ========")
    for i, rec in enumerate(sales, start=1):
        print(f"{i}. 銷售編號: {rec['sid']} - 會員: {rec['mname']} - 日期: {rec['sdate']}")
    print("===============================" )
    choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ").strip()
    if not choice:
        return
    try:
        idx = int(choice)
        if idx < 1 or idx > len(sales):
            raise ValueError
    except ValueError:
        print("=> 錯誤：請輸入有效的數字")
        return
    sid = sales[idx-1]['sid']
    try:
        cur.execute("DELETE FROM sale WHERE sid=?", (sid,))
        conn.commit()
        print(f"=> 銷售編號 {sid} 已刪除")
    except sqlite3.Error:
        conn.rollback()
        print("=> 刪除失敗，請稍後再試。")


def main() -> None:
    conn = connect_db()
    initialize_db(conn)
    while True:
        print("\n***************選單***************")
        print("1. 新增銷售記錄")
        print("2. 顯示銷售報表")
        print("3. 更新銷售記錄")
        print("4. 刪除銷售記錄")
        print("5. 離開")
        print("**********************************")
        choice = input("請選擇操作項目(Enter 離開)：").strip()
        if choice in ["", "5"]:
            print("=> 感謝使用，再見！")
            break
        elif choice == "1":
            add_new_sale(conn)
        elif choice == "2":
            print_sale_report(conn)
        elif choice == "3":
            update_sale_record(conn)
        elif choice == "4":
            delete_sale_record(conn)
        else:
            print("=> 請輸入有效的選項（1-5）")
    conn.close()


if __name__ == '__main__':
    main()

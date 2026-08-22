import streamlit as st
import sqlite3
import pandas as pd
import calendar
from datetime import date, datetime

# =========================================================
# CẤU HÌNH
# =========================================================

st.set_page_config(
    page_title="Quản lý xe cho thuê",
    page_icon="🛵",
    layout="wide"
)

DB_FILE = "quan_ly_xe.db"

STATUS = [
    "Đang rảnh",
    "Đang thuê",
    "Đã trả"
]

EXPENSE_TYPES = [
    "Khấu hao",
    "Thay nhớt",
    "Sửa xe",
    "Thay lốp",
    "Thay bình",
    "Bảo dưỡng",
    "Chi phí khác"
]


# =========================================================
# DATABASE
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()
    cur = conn.cursor()

    # -----------------------------------------------------
    # Bảng xe
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bien_so TEXT NOT NULL UNIQUE,
            ten_xe TEXT NOT NULL,
            gia_ngay REAL DEFAULT 0
        )
    """)

    # -----------------------------------------------------
    # Bảng đơn thuê
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER NOT NULL,
            tu_ngay TEXT NOT NULL,
            den_ngay TEXT NOT NULL,
            trang_thai TEXT NOT NULL,
            tien_thue REAL DEFAULT 0,
            ghi_chu TEXT DEFAULT '',
            FOREIGN KEY(car_id) REFERENCES cars(id)
        )
    """)

    # -----------------------------------------------------
    # Bảng chi phí / khấu hao
    # -----------------------------------------------------

    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER,
            ngay TEXT NOT NULL,
            loai_chi_phi TEXT NOT NULL,
            so_tien REAL DEFAULT 0,
            ghi_chu TEXT DEFAULT '',
            FOREIGN KEY(car_id) REFERENCES cars(id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# DATABASE FUNCTIONS - XE
# =========================================================

def get_cars():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT *
        FROM cars
        ORDER BY id
        """,
        conn
    )

    conn.close()

    return df


def add_car(
    bien_so,
    ten_xe,
    gia_ngay
):

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO cars (
                bien_so,
                ten_xe,
                gia_ngay
            )
            VALUES (?, ?, ?)
            """,
            (
                bien_so,
                ten_xe,
                gia_ngay
            )
        )

        conn.commit()

        result = True

    except sqlite3.IntegrityError:

        result = False

    conn.close()

    return result


def delete_car(car_id):

    conn = get_db()

    # Xóa đơn thuê của xe
    conn.execute(
        """
        DELETE FROM rentals
        WHERE car_id = ?
        """,
        (car_id,)
    )

    # Xóa chi phí của xe
    conn.execute(
        """
        DELETE FROM expenses
        WHERE car_id = ?
        """,
        (car_id,)
    )

    # Xóa xe
    conn.execute(
        """
        DELETE FROM cars
        WHERE id = ?
        """,
        (car_id,)
    )

    conn.commit()
    conn.close()


# =========================================================
# DATABASE FUNCTIONS - ĐƠN THUÊ
# =========================================================

def add_rental(
    car_id,
    tu_ngay,
    den_ngay,
    trang_thai,
    tien_thue,
    ghi_chu
):

    conn = get_db()

    conn.execute(
        """
        INSERT INTO rentals (
            car_id,
            tu_ngay,
            den_ngay,
            trang_thai,
            tien_thue,
            ghi_chu
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            car_id,
            tu_ngay,
            den_ngay,
            trang_thai,
            tien_thue,
            ghi_chu
        )
    )

    conn.commit()
    conn.close()


def get_rentals():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT
            rentals.id,
            rentals.car_id,
            cars.bien_so,
            cars.ten_xe,
            rentals.tu_ngay,
            rentals.den_ngay,
            rentals.trang_thai,
            rentals.tien_thue,
            rentals.ghi_chu

        FROM rentals

        JOIN cars
            ON rentals.car_id = cars.id

        ORDER BY rentals.tu_ngay DESC
        """,
        conn
    )

    conn.close()

    return df


def delete_rental(rental_id):

    conn = get_db()

    conn.execute(
        """
        DELETE FROM rentals
        WHERE id = ?
        """,
        (rental_id,)
    )

    conn.commit()
    conn.close()


# =========================================================
# DATABASE FUNCTIONS - CHI PHÍ
# =========================================================

def add_expense(
    car_id,
    ngay,
    loai_chi_phi,
    so_tien,
    ghi_chu
):

    conn = get_db()

    conn.execute(
        """
        INSERT INTO expenses (
            car_id,
            ngay,
            loai_chi_phi,
            so_tien,
            ghi_chu
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            car_id,
            ngay,
            loai_chi_phi,
            so_tien,
            ghi_chu
        )
    )

    conn.commit()
    conn.close()


def get_expenses():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT
            expenses.id,
            expenses.car_id,
            cars.bien_so,
            cars.ten_xe,
            expenses.ngay,
            expenses.loai_chi_phi,
            expenses.so_tien,
            expenses.ghi_chu

        FROM expenses

        LEFT JOIN cars
            ON expenses.car_id = cars.id

        ORDER BY expenses.ngay DESC
        """,
        conn
    )

    conn.close()

    return df


def delete_expense(expense_id):

    conn = get_db()

    conn.execute(
        """
        DELETE FROM expenses
        WHERE id = ?
        """,
        (expense_id,)
    )

    conn.commit()
    conn.close()


# =========================================================
# TÍNH TRẠNG THÁI XE THEO NGÀY
# =========================================================

def get_status_for_day(
    car_id,
    day
):

    rentals = get_rentals()

    if rentals.empty:

        return "Đang rảnh", 0

    for _, row in rentals.iterrows():

        if int(row["car_id"]) != int(car_id):
            continue

        tu = datetime.strptime(
            row["tu_ngay"],
            "%Y-%m-%d"
        ).date()

        den = datetime.strptime(
            row["den_ngay"],
            "%Y-%m-%d"
        ).date()

        if tu <= day <= den:

            return (
                row["trang_thai"],
                row["tien_thue"]
            )

    return "Đang rảnh", 0


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🛵 QUẢN LÝ XE")

page = st.sidebar.radio(
    "Chức năng",
    [
        "📅 Lịch xe",
        "🛵 Quản lý xe",
        "📋 Đơn thuê",
        "🔧 Chi phí / Khấu hao",
        "💰 Doanh thu 12 tháng"
    ]
)

st.sidebar.divider()

year = st.sidebar.selectbox(
    "Năm",
    range(2024, 2031),
    index=2
)

month = st.sidebar.selectbox(
    "Tháng",
    range(1, 13),
    index=date.today().month - 1,
    format_func=lambda x: f"Tháng {x}"
)


# =========================================================
# QUẢN LÝ XE
# =========================================================

if page == "🛵 Quản lý xe":

    st.title("🛵 Quản lý xe")

    st.subheader("➕ Thêm xe")

    col1, col2, col3 = st.columns(3)

    with col1:

        bien_so = st.text_input(
            "Biển số"
        )

    with col2:

        ten_xe = st.text_input(
            "Tên xe"
        )

    with col3:

        gia_ngay = st.number_input(
            "Giá thuê/ngày",
            min_value=0,
            value=500000,
            step=50000
        )

    if st.button(
        "➕ Thêm xe",
        type="primary"
    ):

        if not bien_so:

            st.error(
                "Vui lòng nhập biển số."
            )

        elif not ten_xe:

            st.error(
                "Vui lòng nhập tên xe."
            )

        else:

            ok = add_car(
                bien_so.strip(),
                ten_xe.strip(),
                gia_ngay
            )

            if ok:

                st.success(
                    "Đã thêm xe."
                )

                st.rerun()

            else:

                st.error(
                    "Biển số này đã tồn tại."
                )

    st.divider()

    st.subheader("🚘 Danh sách xe")

    cars = get_cars()

    if cars.empty:

        st.info(
            "Chưa có xe nào. Hãy thêm xe ở phía trên."
        )

    else:

        for _, car in cars.iterrows():

            col1, col2, col3, col4 = st.columns(
                [1.5, 2, 1.5, 1]
            )

            col1.write(
                f"**{car['bien_so']}**"
            )

            col2.write(
                car["ten_xe"]
            )

            col3.write(
                f"{car['gia_ngay']:,.0f} đ/ngày"
            )

            if col4.button(
                "🗑️ Xóa",
                key=f"delete_car_{car['id']}"
            ):

                delete_car(
                    car["id"]
                )

                st.rerun()


# =========================================================
# ĐƠN THUÊ
# =========================================================

elif page == "📋 Đơn thuê":

    st.title("📋 Quản lý đơn thuê")

    cars = get_cars()

    if cars.empty:

        st.warning(
            "Chưa có xe. Hãy vào 'Quản lý xe' để thêm xe."
        )

    else:

        st.subheader("➕ Tạo thời gian thuê")

        car_options = {
            f"{row['bien_so']} - {row['ten_xe']}":
                row["id"]
            for _, row in cars.iterrows()
        }

        selected_car = st.selectbox(
            "Chọn xe",
            list(car_options.keys())
        )

        car_id = car_options[selected_car]

        car_info = cars[
            cars["id"] == car_id
        ].iloc[0]

        col1, col2 = st.columns(2)

        with col1:

            tu_ngay = st.date_input(
                "Từ ngày",
                value=date.today()
            )

        with col2:

            den_ngay = st.date_input(
                "Đến ngày",
                value=date.today()
            )

        trang_thai = st.selectbox(
            "Trạng thái",
            STATUS
        )

        # -------------------------------------------------
        # Tính số ngày
        # -------------------------------------------------

        if den_ngay >= tu_ngay:

            so_ngay = (
                den_ngay - tu_ngay
            ).days + 1

        else:

            so_ngay = 0

        st.info(
            f"📅 Số ngày: **{so_ngay} ngày**"
        )

        # -------------------------------------------------
        # Tiền mặc định
        # -------------------------------------------------

        tien_mac_dinh = (
            so_ngay * car_info["gia_ngay"]
        )

        tien_thue = st.number_input(
            "Tổng tiền thuê",
            min_value=0,
            value=int(tien_mac_dinh),
            step=50000
        )

        ghi_chu = st.text_area(
            "Ghi chú",
            placeholder=(
                "Tên khách, số điện thoại, "
                "tiền cọc..."
            )
        )

        if st.button(
            "💾 Lưu đơn thuê",
            type="primary"
        ):

            if den_ngay < tu_ngay:

                st.error(
                    "Ngày kết thúc không được nhỏ hơn "
                    "ngày bắt đầu."
                )

            else:

                add_rental(
                    car_id,
                    tu_ngay.strftime("%Y-%m-%d"),
                    den_ngay.strftime("%Y-%m-%d"),
                    trang_thai,
                    tien_thue,
                    ghi_chu
                )

                st.success(
                    "Đã lưu đơn thuê."
                )

                st.rerun()

    st.divider()

    st.subheader("📋 Danh sách đơn")

    rentals = get_rentals()

    if rentals.empty:

        st.info(
            "Chưa có đơn thuê."
        )

    else:

        show_df = rentals.copy()

        show_df["tien_thue"] = (
            show_df["tien_thue"]
            .apply(
                lambda x: f"{x:,.0f} đ"
            )
        )

        show_df = show_df.rename(
            columns={
                "bien_so": "Biển số",
                "ten_xe": "Tên xe",
                "tu_ngay": "Từ ngày",
                "den_ngay": "Đến ngày",
                "trang_thai": "Trạng thái",
                "tien_thue": "Tiền thuê",
                "ghi_chu": "Ghi chú"
            }
        )

        st.dataframe(
            show_df[
                [
                    "Biển số",
                    "Tên xe",
                    "Từ ngày",
                    "Đến ngày",
                    "Trạng thái",
                    "Tiền thuê",
                    "Ghi chú"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        st.subheader("🗑️ Xóa đơn")

        rental_id = st.selectbox(
            "Chọn đơn cần xóa",
            rentals["id"].tolist(),
            format_func=lambda x:
                f"Đơn #{x}"
        )

        if st.button(
            "🗑️ Xóa đơn",
            type="secondary"
        ):

            delete_rental(
                rental_id
            )

            st.success(
                "Đã xóa đơn."
            )

            st.rerun()


# =========================================================
# CHI PHÍ / KHẤU HAO
# =========================================================

elif page == "🔧 Chi phí / Khấu hao":

    st.title("🔧 Chi phí / Khấu hao")

    st.caption(
        "Các khoản chi phí sẽ được trừ vào doanh thu "
        "của tháng phát sinh."
    )

    cars = get_cars()

    if cars.empty:

        st.warning(
            "Chưa có xe. Hãy vào 'Quản lý xe' để thêm xe."
        )

    else:

        st.subheader("➕ Thêm chi phí")

        # -------------------------------------------------
        # Chọn xe
        # -------------------------------------------------

        car_options = {
            "🌐 Chi phí chung": None
        }

        car_options.update({
            f"{row['bien_so']} - {row['ten_xe']}":
                row["id"]
            for _, row in cars.iterrows()
        })

        selected_car = st.selectbox(
            "Xe",
            list(car_options.keys())
        )

        car_id = car_options[selected_car]

        # -------------------------------------------------
        # Ngày + loại chi phí
        # -------------------------------------------------

        col1, col2 = st.columns(2)

        with col1:

            ngay_chi = st.date_input(
                "Ngày phát sinh",
                value=date.today()
            )

        with col2:

            loai_chi_phi = st.selectbox(
                "Loại chi phí",
                EXPENSE_TYPES
            )

        # -------------------------------------------------
        # Số tiền
        # -------------------------------------------------

        so_tien = st.number_input(
            "Số tiền",
            min_value=0,
            value=0,
            step=50000
        )

        ghi_chu = st.text_area(
            "Ghi chú",
            placeholder=(
                "Ví dụ: Thay nhớt lần 2, "
                "sửa phanh, thay lốp..."
            )
        )

        # -------------------------------------------------
        # Lưu
        # -------------------------------------------------

        if st.button(
            "💾 Lưu chi phí",
            type="primary"
        ):

            if so_tien <= 0:

                st.error(
                    "Vui lòng nhập số tiền lớn hơn 0."
                )

            else:

                add_expense(
                    car_id,
                    ngay_chi.strftime("%Y-%m-%d"),
                    loai_chi_phi,
                    so_tien,
                    ghi_chu
                )

                st.success(
                    "Đã lưu chi phí."
                )

                st.rerun()

    st.divider()

    # =====================================================
    # DANH SÁCH CHI PHÍ
    # =====================================================

    st.subheader("📋 Danh sách chi phí")

    expenses = get_expenses()

    if expenses.empty:

        st.info(
            "Chưa có khoản chi phí nào."
        )

    else:

        show_expenses = expenses.copy()

        show_expenses["Xe"] = (
            show_expenses["bien_so"]
            .fillna("Chi phí chung")
        )

        show_expenses["Số tiền"] = (
            show_expenses["so_tien"]
            .apply(
                lambda x: f"{x:,.0f} đ"
            )
        )

        show_expenses = show_expenses.rename(
            columns={
                "ngay": "Ngày",
                "loai_chi_phi": "Loại chi phí",
                "ghi_chu": "Ghi chú"
            }
        )

        st.dataframe(
            show_expenses[
                [
                    "Xe",
                    "Ngày",
                    "Loại chi phí",
                    "Số tiền",
                    "Ghi chú"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

        # -------------------------------------------------
        # Tổng chi phí
        # -------------------------------------------------

        total_expenses = expenses[
            "so_tien"
        ].sum()

        st.metric(
            "💸 Tổng chi phí",
            f"{total_expenses:,.0f} đ"
        )

        # -------------------------------------------------
        # Xóa chi phí
        # -------------------------------------------------

        st.subheader("🗑️ Xóa chi phí")

        expense_id = st.selectbox(
            "Chọn khoản chi phí cần xóa",
            expenses["id"].tolist(),
            format_func=lambda x:
                f"Chi phí #{x}"
        )

        if st.button(
            "🗑️ Xóa chi phí"
        ):

            delete_expense(
                expense_id
            )

            st.success(
                "Đã xóa chi phí."
            )

            st.rerun()


# =========================================================
# LỊCH XE
# =========================================================

elif page == "📅 Lịch xe":

    st.title("📅 Lịch xe")

    st.subheader(
        f"Tháng {month}/{year}"
    )

    cars = get_cars()

    if cars.empty:

        st.info(
            "Chưa có xe nào. "
            "Vào 'Quản lý xe' để thêm xe."
        )

    else:

        days_in_month = calendar.monthrange(
            year,
            month
        )[1]

        table = []

        for _, car in cars.iterrows():

            row = {
                "Xe":
                    f"{car['bien_so']} - "
                    f"{car['ten_xe']}"
            }

            for day in range(
                1,
                days_in_month + 1
            ):

                current_day = date(
                    year,
                    month,
                    day
                )

                status, _ = get_status_for_day(
                    car["id"],
                    current_day
                )

                if status == "Đang thuê":

                    text = "🟠 Thuê"

                elif status == "Đã trả":

                    text = "🔵 Trả"

                else:

                    text = "🟢 Rảnh"

                row[str(day)] = text

            table.append(row)

        df = pd.DataFrame(
            table
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown(
            """
            🟢 **Đang rảnh** &nbsp;&nbsp;
            🟠 **Đang thuê** &nbsp;&nbsp;
            🔵 **Đã trả**
            """
        )


# =========================================================
# DOANH THU 12 THÁNG
# =========================================================

elif page == "💰 Doanh thu 12 tháng":

    st.title("💰 Doanh thu 12 tháng")

    cars = get_cars()
    rentals = get_rentals()
    expenses = get_expenses()

    # =====================================================
    # TÍNH DOANH THU TỪNG THÁNG
    # =====================================================

    monthly_data = []

    for m in range(1, 13):

        total_revenue = 0
        total_expense = 0
        rental_days = 0

        # =================================================
        # DOANH THU THUÊ XE
        # =================================================

        if not rentals.empty:

            for _, rental in rentals.iterrows():

                tu = datetime.strptime(
                    rental["tu_ngay"],
                    "%Y-%m-%d"
                ).date()

                den = datetime.strptime(
                    rental["den_ngay"],
                    "%Y-%m-%d"
                ).date()

                # Ngày đầu tháng
                first_day = date(
                    year,
                    m,
                    1
                )

                # Ngày cuối tháng
                last_day = date(
                    year,
                    m,
                    calendar.monthrange(
                        year,
                        m
                    )[1]
                )

                # Khoảng giao nhau
                start = max(
                    tu,
                    first_day
                )

                end = min(
                    den,
                    last_day
                )

                if start <= end:

                    days = (
                        end - start
                    ).days + 1

                    total_rental_days = (
                        den - tu
                    ).days + 1

                    # Phân bổ tiền thuê theo ngày
                    daily_price = (
                        rental["tien_thue"]
                        / total_rental_days
                    )

                    total_revenue += (
                        daily_price * days
                    )

                    rental_days += days

        # =================================================
        # CHI PHÍ / KHẤU HAO
        # =================================================

        if not expenses.empty:

            for _, expense in expenses.iterrows():

                expense_date = datetime.strptime(
                    expense["ngay"],
                    "%Y-%m-%d"
                ).date()

                if (
                    expense_date.year == year
                    and expense_date.month == m
                ):

                    total_expense += (
                        expense["so_tien"]
                    )

        # =================================================
        # DOANH THU THỰC TẾ
        # =================================================

        net_revenue = (
            total_revenue
            - total_expense
        )

        monthly_data.append({
            "Tháng": f"Tháng {m}",
            "Số ngày thuê": rental_days,
            "Doanh thu": total_revenue,
            "Chi phí / Khấu hao": total_expense,
            "Doanh thu thực tế": net_revenue
        })

    revenue_df = pd.DataFrame(
        monthly_data
    )

    # =====================================================
    # TỔNG NĂM
    # =====================================================

    total_year = revenue_df[
        "Doanh thu"
    ].sum()

    total_expense_year = revenue_df[
        "Chi phí / Khấu hao"
    ].sum()

    net_year = revenue_df[
        "Doanh thu thực tế"
    ].sum()

    total_days = revenue_df[
        "Số ngày thuê"
    ].sum()

    # =====================================================
    # KPI
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        f"💰 Doanh thu cho thuê {year}",
        f"{total_year:,.0f} đ"
    )

    col2.metric(
        "🔧 Chi phí / Khấu hao",
        f"{total_expense_year:,.0f} đ"
    )

    col3.metric(
        "💵 Doanh thu thực tế",
        f"{net_year:,.0f} đ"
    )

    col4.metric(
        "📅 Tổng ngày thuê",
        f"{total_days:,.0f} ngày"
    )

    st.divider()

    # =====================================================
    # BẢNG DOANH THU
    # =====================================================

    st.subheader(
        f"📋 Chi tiết doanh thu năm {year}"
    )

    display_df = revenue_df.copy()

    for col in [
        "Doanh thu",
        "Chi phí / Khấu hao",
        "Doanh thu thực tế"
    ]:

        display_df[col] = (
            display_df[col]
            .apply(
                lambda x:
                f"{x:,.0f} đ"
            )
        )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # BIỂU ĐỒ
    # =====================================================

    st.subheader(
        f"📊 Biểu đồ doanh thu thực tế năm {year}"
    )

    chart_df = revenue_df.copy()

    chart_df = chart_df.set_index(
        "Tháng"
    )

    st.bar_chart(
        chart_df[
            "Doanh thu thực tế"
        ]
    )

    # =====================================================
    # BIỂU ĐỒ DOANH THU VS CHI PHÍ
    # =====================================================

    st.subheader(
        "📊 Doanh thu và chi phí"
    )

    compare_df = revenue_df[
        [
            "Doanh thu",
            "Chi phí / Khấu hao"
        ]
    ].copy()

    compare_df.index = revenue_df[
        "Tháng"
    ]

    st.bar_chart(
        compare_df
    )
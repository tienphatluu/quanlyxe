import streamlit as st
import sqlite3
import pandas as pd
import calendar

from datetime import (
    date,
    datetime,
    timedelta
)


# =========================================================
# CẤU HÌNH
# =========================================================

st.set_page_config(
    page_title="Quản lý xe cho thuê",
    page_icon="🛵",
    layout="wide",
    initial_sidebar_state="expanded"
)


DB_FILE = "quan_ly_xe.db"


# =========================================================
# MẬT KHẨU ADMIN
# =========================================================

ADMIN_PASSWORD = "Phung02101997"


# =========================================================
# TRẠNG THÁI
# =========================================================

STATUS = [
    "Đang rảnh",
    "Đang thuê",
    "Đã trả"
]


# =========================================================
# LOẠI CHI PHÍ
# =========================================================

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
# SESSION STATE
# =========================================================

if "admin_logged_in" not in st.session_state:

    st.session_state.admin_logged_in = False


if "current_page" not in st.session_state:

    st.session_state.current_page = None


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
    <style>

    /* -----------------------------------------
       GIAO DIỆN CHUNG
       ----------------------------------------- */

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }


    /* -----------------------------------------
       KPI
       ----------------------------------------- */

    div[data-testid="stMetric"] {

        background-color: rgba(128,128,128,0.08);

        padding: 14px;

        border-radius: 10px;

        border: 1px solid rgba(128,128,128,0.12);
    }


    /* -----------------------------------------
       BUTTON
       ----------------------------------------- */

    .stButton button {

        border-radius: 8px;

        font-weight: 500;
    }


    /* -----------------------------------------
       DATAFRAME
       ----------------------------------------- */

    div[data-testid="stDataFrame"] {

        border-radius: 8px;
    }


    /* -----------------------------------------
       SIDEBAR
       ----------------------------------------- */

    section[data-testid="stSidebar"] {

        transition:
            width 0.25s ease,
            min-width 0.25s ease;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# DATABASE
# =========================================================

def get_db():

    conn = sqlite3.connect(
        DB_FILE
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# KHỞI TẠO DATABASE
# =========================================================

def init_db():

    conn = get_db()

    cur = conn.cursor()


    # =====================================================
    # BẢNG XE
    # =====================================================

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS cars (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            bien_so TEXT NOT NULL UNIQUE,

            ten_xe TEXT NOT NULL,

            gia_ngay REAL DEFAULT 0
        )
        """
    )


    # =====================================================
    # BẢNG ĐƠN THUÊ
    # =====================================================

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rentals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            car_id INTEGER NOT NULL,

            tu_ngay TEXT NOT NULL,

            den_ngay TEXT NOT NULL,

            trang_thai TEXT NOT NULL,

            tien_thue REAL DEFAULT 0,

            ghi_chu TEXT DEFAULT '',

            FOREIGN KEY(car_id)
                REFERENCES cars(id)
        )
        """
    )


    # =====================================================
    # BẢNG CHI PHÍ
    # =====================================================

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            car_id INTEGER,

            ngay TEXT NOT NULL,

            loai_chi_phi TEXT NOT NULL,

            so_tien REAL DEFAULT 0,

            ghi_chu TEXT DEFAULT '',

            FOREIGN KEY(car_id)
                REFERENCES cars(id)
        )
        """
    )


    conn.commit()

    conn.close()


init_db()


# =========================================================
# HÀM HỖ TRỢ
# =========================================================

def format_money(value):

    try:

        value = float(value)

    except:

        value = 0

    return f"{value:,.0f} đ"


# =========================================================

def parse_date(value):

    return datetime.strptime(
        str(value),
        "%Y-%m-%d"
    ).date()


# =========================================================

def number_of_days(
    start_date,
    end_date
):

    if end_date < start_date:

        return 0

    return (
        end_date - start_date
    ).days + 1


# =========================================================
# XE
# =========================================================

def get_cars():

    conn = get_db()

    df = pd.read_sql_query(
        """
        SELECT
            *
        FROM cars
        ORDER BY id
        """,
        conn
    )

    conn.close()

    return df


# =========================================================

def add_car(
    bien_so,
    ten_xe,
    gia_ngay
):

    conn = get_db()

    try:

        conn.execute(
            """
            INSERT INTO cars
            (
                bien_so,
                ten_xe,
                gia_ngay
            )

            VALUES
            (?, ?, ?)
            """,
            (
                bien_so.strip(),
                ten_xe.strip(),
                gia_ngay
            )
        )

        conn.commit()

        result = True

    except sqlite3.IntegrityError:

        result = False

    finally:

        conn.close()

    return result


# =========================================================

def delete_car(car_id):

    conn = get_db()

    # Xóa đơn thuê
    conn.execute(
        """
        DELETE FROM rentals
        WHERE car_id = ?
        """,
        (car_id,)
    )

    # Xóa chi phí
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
# ĐƠN THUÊ
# =========================================================

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

        ORDER BY
            rentals.tu_ngay DESC
        """,
        conn
    )

    conn.close()

    return df


# =========================================================

def rental_has_conflict(
    car_id,
    tu_ngay,
    den_ngay
):

    rentals = get_rentals()

    if rentals.empty:

        return False


    for _, row in rentals.iterrows():

        if int(row["car_id"]) != int(car_id):

            continue


        old_start = parse_date(
            row["tu_ngay"]
        )

        old_end = parse_date(
            row["den_ngay"]
        )


        # Có giao nhau
        if (
            tu_ngay <= old_end
            and
            den_ngay >= old_start
        ):

            return True


    return False


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
        INSERT INTO rentals
        (
            car_id,
            tu_ngay,
            den_ngay,
            trang_thai,
            tien_thue,
            ghi_chu
        )

        VALUES
        (?, ?, ?, ?, ?, ?)
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


# =========================================================

def delete_rental(
    rental_id
):

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
# CHI PHÍ
# =========================================================

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

        ORDER BY
            expenses.ngay DESC
        """,
        conn
    )

    conn.close()

    return df


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
        INSERT INTO expenses
        (
            car_id,
            ngay,
            loai_chi_phi,
            so_tien,
            ghi_chu
        )

        VALUES
        (?, ?, ?, ?, ?)
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


# =========================================================

def delete_expense(
    expense_id
):

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
# TRẠNG THÁI XE THEO NGÀY
# =========================================================

def get_status_for_day(
    car_id,
    day
):

    rentals = get_rentals()

    if rentals.empty:

        return (
            "Đang rảnh",
            0,
            None
        )


    for _, row in rentals.iterrows():

        if int(row["car_id"]) != int(car_id):

            continue


        tu = parse_date(
            row["tu_ngay"]
        )

        den = parse_date(
            row["den_ngay"]
        )


        if (
            tu <= day <= den
        ):

            return (
                row["trang_thai"],
                row["tien_thue"],
                row
            )


    return (
        "Đang rảnh",
        0,
        None
    )


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title(
    "🛵 QUẢN LÝ XE"
)


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


# =========================================================
# TỰ ĐỘNG ĐĂNG XUẤT ADMIN KHI RỜI QUẢN LÝ XE
# =========================================================

if (
    st.session_state.current_page
    is not None
    and
    st.session_state.current_page
    != page
):

    if (
        st.session_state.current_page
        == "🛵 Quản lý xe"
    ):

        st.session_state.admin_logged_in = False


st.session_state.current_page = page


# =========================================================
# NĂM / THÁNG
# =========================================================

st.sidebar.divider()


year = st.sidebar.selectbox(
    "Năm",
    range(
        2024,
        2031
    ),
    index=(
        list(
            range(
                2024,
                2031
            )
        ).index(
            min(
                max(
                    date.today().year,
                    2024
                ),
                2030
            )
        )
    )
)


month = st.sidebar.selectbox(
    "Tháng",
    range(
        1,
        13
    ),
    index=(
        date.today().month - 1
    ),
    format_func=lambda x:
        f"Tháng {x}"
)


# =========================================================
# SIDEBAR TỰ THU GỌN
# =========================================================

if page in [
    "📅 Lịch xe",
    "🛵 Quản lý xe"
]:

    # Dùng CSS/JS nhẹ để đóng sidebar
    st.markdown(
        """
        <script>

        const sidebar =
            window.parent.document
            .querySelector(
                'section[data-testid="stSidebar"]'
            );

        if (sidebar) {

            sidebar.style.width = "0px";
            sidebar.style.minWidth = "0px";
        }

        </script>
        """,
        unsafe_allow_html=True
    )


# =========================================================
# TRANG QUẢN LÝ XE
# =========================================================

if page == "🛵 Quản lý xe":

    st.title(
        "🛵 Quản lý xe"
    )


    # =====================================================
    # CHƯA ĐĂNG NHẬP
    # =====================================================

    if not st.session_state.admin_logged_in:

        st.warning(
            "🔐 Trang này yêu cầu quyền Admin."
        )


        st.subheader(
            "🔑 Đăng nhập Admin"
        )


        with st.form(
            "admin_login"
        ):

            password = st.text_input(
                "Mật khẩu Admin",
                type="password"
            )


            login_button = st.form_submit_button(
                "🔐 Đăng nhập",
                type="primary"
            )


            if login_button:

                if password == ADMIN_PASSWORD:

                    st.session_state.admin_logged_in = True


                    st.success(
                        "✅ Đăng nhập Admin thành công!"
                    )


                    st.toast(
                        "Admin đã đăng nhập",
                        icon="🔐"
                    )


                    st.rerun()

                else:

                    st.error(
                        "❌ Mật khẩu không đúng."
                    )


        st.info(
            "Khi rời khỏi trang Quản lý xe, "
            "quyền Admin sẽ tự động đăng xuất."
        )


        st.stop()


    # =====================================================
    # ADMIN ĐÃ ĐĂNG NHẬP
    # =====================================================

    col_admin1, col_admin2 = st.columns(
        [5, 1]
    )


    with col_admin1:

        st.success(
            "🔐 Đang đăng nhập với quyền ADMIN"
        )


    with col_admin2:

        if st.button(
            "🚪 Thoát Admin"
        ):

            st.session_state.admin_logged_in = False

            st.success(
                "Đã đăng xuất Admin."
            )

            st.rerun()


    st.divider()


    # =====================================================
    # THÊM XE
    # =====================================================

    st.subheader(
        "➕ Thêm xe"
    )


    col1, col2, col3 = st.columns(
        3
    )


    with col1:

        bien_so = st.text_input(
            "Biển số",
            placeholder="29A1-12345"
        )


    with col2:

        ten_xe = st.text_input(
            "Tên xe",
            placeholder="Honda SH 160"
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
        type="primary",
        key="add_car"
    ):

        if not bien_so.strip():

            st.error(
                "❌ Vui lòng nhập biển số."
            )

        elif not ten_xe.strip():

            st.error(
                "❌ Vui lòng nhập tên xe."
            )

        else:

            ok = add_car(
                bien_so,
                ten_xe,
                gia_ngay
            )


            if ok:

                st.success(
                    f"✅ Đã thêm xe {bien_so} thành công!"
                )

                st.toast(
                    f"Đã thêm xe {bien_so}",
                    icon="🛵"
                )

                st.rerun()

            else:

                st.error(
                    "❌ Biển số này đã tồn tại."
                )


    st.divider()


    # =====================================================
    # DANH SÁCH XE
    # =====================================================

    st.subheader(
        "🚘 Danh sách xe"
    )


    cars = get_cars()


    if cars.empty:

        st.info(
            "Chưa có xe nào."
        )

    else:

        for _, car in cars.iterrows():

            c1, c2, c3, c4 = st.columns(
                [
                    1.5,
                    2.5,
                    1.7,
                    1
                ]
            )


            with c1:

                st.write(
                    f"**{car['bien_so']}**"
                )


            with c2:

                st.write(
                    car["ten_xe"]
                )


            with c3:

                st.write(
                    f"{format_money(car['gia_ngay'])}/ngày"
                )


            with c4:

                if st.button(
                    "🗑️ Xóa",
                    key=f"delete_car_{car['id']}"
                ):

                    delete_car(
                        car["id"]
                    )

                    st.success(
                        f"✅ Đã xóa xe {car['bien_so']}."
                    )

                    st.toast(
                        "Đã xóa xe",
                        icon="🗑️"
                    )

                    st.rerun()


# =========================================================
# TRANG ĐƠN THUÊ
# =========================================================

elif page == "📋 Đơn thuê":

    st.title(
        "📋 Quản lý đơn thuê"
    )


    cars = get_cars()


    # =====================================================
    # TẠO ĐƠN
    # =====================================================

    if cars.empty:

        st.warning(
            "⚠️ Chưa có xe. "
            "Hãy vào Quản lý xe để thêm xe."
        )

    else:

        st.subheader(
            "➕ Tạo đơn thuê"
        )


        car_options = {

            f"{row['bien_so']} - {row['ten_xe']}":
                row["id"]

            for _, row in cars.iterrows()
        }


        selected_car = st.selectbox(
            "Chọn xe",
            list(
                car_options.keys()
            )
        )


        car_id = car_options[
            selected_car
        ]


        car_info = cars[
            cars["id"] == car_id
        ].iloc[0]


        col1, col2 = st.columns(
            2
        )


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


        so_ngay = number_of_days(
            tu_ngay,
            den_ngay
        )


        st.info(
            f"📅 Số ngày thuê: **{so_ngay} ngày**"
        )


        tien_mac_dinh = (
            so_ngay
            *
            float(
                car_info["gia_ngay"]
            )
        )


        tien_thue = st.number_input(
            "Tổng tiền thuê",
            min_value=0,
            value=int(
                tien_mac_dinh
            ),
            step=50000
        )


        st.caption(
            "💡 Doanh thu sẽ được ghi nhận "
            "toàn bộ vào ngày bắt đầu thuê."
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
            type="primary",
            key="save_rental"
        ):

            if den_ngay < tu_ngay:

                st.error(
                    "❌ Ngày kết thúc không được nhỏ hơn ngày bắt đầu."
                )


            elif rental_has_conflict(
                car_id,
                tu_ngay,
                den_ngay
            ):

                st.error(
                    "❌ Xe này đã có đơn thuê trùng thời gian."
                )

                st.warning(
                    "Vui lòng chọn thời gian khác "
                    "hoặc chọn xe khác."
                )


            elif tien_thue <= 0:

                st.error(
                    "❌ Tổng tiền thuê phải lớn hơn 0."
                )


            else:

                add_rental(
                    car_id,
                    tu_ngay.strftime(
                        "%Y-%m-%d"
                    ),
                    den_ngay.strftime(
                        "%Y-%m-%d"
                    ),
                    trang_thai,
                    tien_thue,
                    ghi_chu
                )


                st.success(
                    "✅ Đã lưu đơn thuê thành công!"
                )


                st.toast(
                    "Đã thêm đơn thuê",
                    icon="✅"
                )


                st.rerun()


    st.divider()


    # =====================================================
    # DANH SÁCH ĐƠN
    # =====================================================

    st.subheader(
        "📋 Danh sách đơn"
    )


    rentals = get_rentals()


    if rentals.empty:

        st.info(
            "Chưa có đơn thuê."
        )

    else:

        show_df = rentals.copy()


        show_df["tien_thue"] = (
            show_df[
                "tien_thue"
            ]
            .apply(
                format_money
            )
        )


        show_df = show_df.rename(
            columns={

                "bien_so":
                    "Biển số",

                "ten_xe":
                    "Tên xe",

                "tu_ngay":
                    "Từ ngày",

                "den_ngay":
                    "Đến ngày",

                "trang_thai":
                    "Trạng thái",

                "tien_thue":
                    "Tiền thuê",

                "ghi_chu":
                    "Ghi chú"
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


        st.subheader(
            "🗑️ Xóa đơn"
        )


        rental_id = st.selectbox(
            "Chọn đơn cần xóa",
            rentals["id"].tolist(),
            format_func=lambda x:
                f"Đơn #{x}"
        )


        if st.button(
            "🗑️ Xóa đơn",
            key="delete_rental"
        ):

            delete_rental(
                rental_id
            )


            st.success(
                f"✅ Đã xóa đơn #{rental_id}."
            )


            st.toast(
                "Đã xóa đơn thuê",
                icon="🗑️"
            )


            st.rerun()


# =========================================================
# TRANG CHI PHÍ
# =========================================================

elif page == "🔧 Chi phí / Khấu hao":

    st.title(
        "🔧 Chi phí / Khấu hao"
    )


    st.caption(
        "Chi phí được ghi nhận vào đúng ngày phát sinh."
    )


    cars = get_cars()


    if cars.empty:

        st.warning(
            "Chưa có xe."
        )

    else:

        st.subheader(
            "➕ Thêm chi phí"
        )


        car_options = {

            "🌐 Chi phí chung":
                None
        }


        car_options.update({

            f"{row['bien_so']} - {row['ten_xe']}":
                row["id"]

            for _, row in cars.iterrows()
        })


        selected_car = st.selectbox(
            "Xe",
            list(
                car_options.keys()
            )
        )


        car_id = car_options[
            selected_car
        ]


        col1, col2 = st.columns(
            2
        )


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


        so_tien = st.number_input(
            "Số tiền",
            min_value=0,
            value=0,
            step=50000
        )


        ghi_chu = st.text_area(
            "Ghi chú",
            placeholder=(
                "Ví dụ: thay nhớt, "
                "sửa phanh, thay lốp..."
            )
        )


        if st.button(
            "💾 Lưu chi phí",
            type="primary",
            key="save_expense"
        ):

            if so_tien <= 0:

                st.error(
                    "❌ Số tiền phải lớn hơn 0."
                )

            else:

                add_expense(
                    car_id,
                    ngay_chi.strftime(
                        "%Y-%m-%d"
                    ),
                    loai_chi_phi,
                    so_tien,
                    ghi_chu
                )


                st.success(
                    "✅ Đã lưu chi phí thành công!"
                )


                st.toast(
                    "Đã thêm chi phí",
                    icon="🔧"
                )


                st.rerun()


    st.divider()


    # =====================================================
    # DANH SÁCH CHI PHÍ
    # =====================================================

    st.subheader(
        "📋 Danh sách chi phí"
    )


    expenses = get_expenses()


    if expenses.empty:

        st.info(
            "Chưa có khoản chi phí nào."
        )

    else:

        show_expenses = expenses.copy()


        show_expenses["Xe"] = (
            show_expenses[
                "bien_so"
            ]
            .fillna(
                "Chi phí chung"
            )
        )


        show_expenses["Số tiền"] = (
            show_expenses[
                "so_tien"
            ]
            .apply(
                format_money
            )
        )


        show_expenses = show_expenses.rename(
            columns={

                "ngay":
                    "Ngày",

                "loai_chi_phi":
                    "Loại chi phí",

                "ghi_chu":
                    "Ghi chú"
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


        total_expenses = (
            expenses[
                "so_tien"
            ]
            .sum()
        )


        st.metric(
            "💸 Tổng chi phí",
            format_money(
                total_expenses
            )
        )


        st.subheader(
            "🗑️ Xóa chi phí"
        )


        expense_id = st.selectbox(
            "Chọn khoản chi phí",
            expenses["id"].tolist(),
            format_func=lambda x:
                f"Chi phí #{x}"
        )


        if st.button(
            "🗑️ Xóa chi phí",
            key="delete_expense"
        ):

            delete_expense(
                expense_id
            )


            st.success(
                f"✅ Đã xóa chi phí #{expense_id}."
            )


            st.toast(
                "Đã xóa chi phí",
                icon="🗑️"
            )


            st.rerun()


# =========================================================
# LỊCH XE
# =========================================================

elif page == "📅 Lịch xe":

    st.title(
        "📅 Lịch xe"
    )


    st.subheader(
        f"Tháng {month}/{year}"
    )


    cars = get_cars()


    if cars.empty:

        st.info(
            "Chưa có xe nào."
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


                status, _, _ = (
                    get_status_for_day(
                        car["id"],
                        current_day
                    )
                )


                if status == "Đang thuê":

                    text = "🟠 Thuê"

                elif status == "Đã trả":

                    text = "🔵 Trả"

                else:

                    text = "🟢 Rảnh"


                row[
                    str(day)
                ] = text


            table.append(
                row
            )


        df = pd.DataFrame(
            table
        )


        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=550
        )


        st.markdown(
            """
            🟢 **Rảnh**
            &nbsp;&nbsp;&nbsp;
            🟠 **Đang thuê**
            &nbsp;&nbsp;&nbsp;
            🔵 **Đã trả**
            """
        )


# =========================================================
# DOANH THU
# =========================================================

elif page == "💰 Doanh thu 12 tháng":

    st.title(
        "💰 Doanh thu"
    )


    rentals = get_rentals()

    expenses = get_expenses()


    # =====================================================
    # DOANH THU 12 THÁNG
    #
    # QUY TẮC:
    #
    # Đơn 01/08 -> 05/08
    # Tổng tiền 2.500.000
    #
    # 01/08 = +2.500.000
    #
    # 02/08 -> 05/08
    # Không cộng thêm doanh thu
    # =====================================================


    monthly_data = []


    for m in range(
        1,
        13
    ):

        total_revenue = 0

        total_expense = 0

        rental_days = 0


        # =================================================
        # DOANH THU
        # CHỈ TÍNH NGÀY BẮT ĐẦU
        # =================================================

        if not rentals.empty:

            for _, rental in rentals.iterrows():

                tu = parse_date(
                    rental["tu_ngay"]
                )

                den = parse_date(
                    rental["den_ngay"]
                )


                # -----------------------------------------
                # CHỈ TÍNH VÀO THÁNG CỦA NGÀY BẮT ĐẦU
                # -----------------------------------------

                if (
                    tu.year == year
                    and
                    tu.month == m
                ):

                    total_revenue += float(
                        rental["tien_thue"]
                    )


                    rental_days += (
                        den - tu
                    ).days + 1


        # =================================================
        # CHI PHÍ
        # =================================================

        if not expenses.empty:

            for _, expense in expenses.iterrows():

                expense_date = parse_date(
                    expense["ngay"]
                )


                if (
                    expense_date.year
                    == year
                    and
                    expense_date.month
                    == m
                ):

                    total_expense += float(
                        expense["so_tien"]
                    )


        # =================================================
        # THỰC THU
        # =================================================

        net_revenue = (
            total_revenue
            -
            total_expense
        )


        monthly_data.append({

            "Tháng":
                f"Tháng {m}",

            "Số ngày thuê":
                rental_days,

            "Doanh thu":
                total_revenue,

            "Chi phí / Khấu hao":
                total_expense,

            "Doanh thu thực tế":
                net_revenue
        })


    revenue_df = pd.DataFrame(
        monthly_data
    )


    # =====================================================
    # TỔNG NĂM
    # =====================================================

    total_year = (
        revenue_df[
            "Doanh thu"
        ]
        .sum()
    )


    total_expense_year = (
        revenue_df[
            "Chi phí / Khấu hao"
        ]
        .sum()
    )


    net_year = (
        revenue_df[
            "Doanh thu thực tế"
        ]
        .sum()
    )


    total_days = (
        revenue_df[
            "Số ngày thuê"
        ]
        .sum()
    )


    # =====================================================
    # KPI
    # =====================================================

    c1, c2, c3, c4 = st.columns(
        4
    )


    c1.metric(
        f"💰 Doanh thu {year}",
        format_money(
            total_year
        )
    )


    c2.metric(
        "🔧 Chi phí / Khấu hao",
        format_money(
            total_expense_year
        )
    )


    c3.metric(
        "💵 Doanh thu thực tế",
        format_money(
            net_year
        )
    )


    c4.metric(
        "📅 Tổng ngày thuê",
        f"{total_days:,.0f} ngày"
    )


    st.divider()


    # =====================================================
    # BẢNG 12 THÁNG
    # =====================================================

    st.subheader(
        f"📋 Tổng hợp doanh thu năm {year}"
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
                format_money
            )
        )


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


    # =====================================================
    # BIỂU ĐỒ DOANH THU THỰC TẾ
    # =====================================================

    st.subheader(
        f"📊 Doanh thu thực tế năm {year}"
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
    # SO SÁNH DOANH THU / CHI PHÍ
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


    # =====================================================
    # DOANH THU THEO NGÀY
    # =====================================================

    st.divider()


    st.header(
        f"📅 Doanh thu theo ngày "
        f"- Tháng {month}/{year}"
    )


    selected_first_day = date(
        year,
        month,
        1
    )


    selected_last_day = date(
        year,
        month,
        calendar.monthrange(
            year,
            month
        )[1]
    )


    daily_data = []


    current_day = (
        selected_first_day
    )


    while (
        current_day
        <=
        selected_last_day
    ):

        daily_revenue = 0

        daily_expense = 0

        rented_cars = []


        # =================================================
        # ĐƠN THUÊ
        # =================================================

        if not rentals.empty:

            for _, rental in rentals.iterrows():

                tu = parse_date(
                    rental["tu_ngay"]
                )

                den = parse_date(
                    rental["den_ngay"]
                )


                # -----------------------------------------
                # CHỈ TÍNH TIỀN Ở NGÀY BẮT ĐẦU
                # -----------------------------------------

                if tu == current_day:

                    daily_revenue += float(
                        rental["tien_thue"]
                    )


                # -----------------------------------------
                # CÁC NGÀY CÒN LẠI:
                # CHỈ HIỂN THỊ TRẠNG THÁI
                # -----------------------------------------

                if (
                    tu
                    <=
                    current_day
                    <=
                    den
                ):

                    rented_cars.append(

                        f"{rental['bien_so']} - "
                        f"{rental['ten_xe']}"

                    )


        # =================================================
        # CHI PHÍ
        # =================================================

        if not expenses.empty:

            for _, expense in expenses.iterrows():

                expense_date = parse_date(
                    expense["ngay"]
                )


                if (
                    expense_date
                    ==
                    current_day
                ):

                    daily_expense += float(
                        expense["so_tien"]
                    )


        # =================================================
        # THỰC THU
        # =================================================

        daily_net = (
            daily_revenue
            -
            daily_expense
        )


        # =================================================
        # TRẠNG THÁI
        # =================================================

        if rented_cars:

            status_text = (
                "🟠 Đang thuê: "
                +
                ", ".join(
                    rented_cars
                )
            )

        else:

            status_text = (
                "🟢 Không có xe đang thuê"
            )


        # =================================================
        # LƯU
        # =================================================

        daily_data.append({

            "Ngày":
                current_day.strftime(
                    "%d/%m/%Y"
                ),

            "Thứ":
                current_day.strftime(
                    "%A"
                ),

            "Trạng thái":
                status_text,

            "Doanh thu":
                daily_revenue,

            "Chi phí":
                daily_expense,

            "Thực thu":
                daily_net
        })


        current_day += timedelta(
            days=1
        )


    daily_df = pd.DataFrame(
        daily_data
    )


    # =====================================================
    # THỨ TIẾNG VIỆT
    # =====================================================

    weekday_map = {

        "Monday":
            "Thứ 2",

        "Tuesday":
            "Thứ 3",

        "Wednesday":
            "Thứ 4",

        "Thursday":
            "Thứ 5",

        "Friday":
            "Thứ 6",

        "Saturday":
            "Thứ 7",

        "Sunday":
            "Chủ nhật"
    }


    daily_df["Thứ"] = (
        daily_df[
            "Thứ"
        ]
        .map(
            weekday_map
        )
    )


    # =====================================================
    # TỔNG THÁNG
    # =====================================================

    month_revenue = (
        daily_df[
            "Doanh thu"
        ]
        .sum()
    )


    month_expense = (
        daily_df[
            "Chi phí"
        ]
        .sum()
    )


    month_net = (
        daily_df[
            "Thực thu"
        ]
        .sum()
    )


    # =====================================================
    # KPI THÁNG
    # =====================================================

    m1, m2, m3 = st.columns(
        3
    )


    m1.metric(
        "💰 Doanh thu tháng",
        format_money(
            month_revenue
        )
    )


    m2.metric(
        "🔧 Chi phí tháng",
        format_money(
            month_expense
        )
    )


    m3.metric(
        "💵 Thực thu tháng",
        format_money(
            month_net
        )
    )


    st.divider()


    # =====================================================
    # BẢNG TỪNG NGÀY
    # =====================================================

    st.subheader(
        f"📋 Chi tiết từng ngày "
        f"- Tháng {month}/{year}"
    )


    display_daily = (
        daily_df.copy()
    )


    # -----------------------------------------------------
    # DOANH THU
    # -----------------------------------------------------

    display_daily[
        "Doanh thu"
    ] = (
        display_daily[
            "Doanh thu"
        ]
        .apply(

            lambda x:
                format_money(x)
                if x > 0
                else "-"
        )
    )


    # -----------------------------------------------------
    # CHI PHÍ
    # -----------------------------------------------------

    display_daily[
        "Chi phí"
    ] = (
        display_daily[
            "Chi phí"
        ]
        .apply(

            lambda x:
                format_money(x)
                if x > 0
                else "-"
        )
    )


    # -----------------------------------------------------
    # THỰC THU
    # -----------------------------------------------------

    display_daily[
        "Thực thu"
    ] = (
        display_daily[
            "Thực thu"
        ]
        .apply(

            lambda x:
                format_money(x)
                if x != 0
                else "-"
        )
    )


    st.dataframe(
        display_daily[
            [
                "Ngày",
                "Thứ",
                "Trạng thái",
                "Doanh thu",
                "Chi phí",
                "Thực thu"
            ]
        ],
        use_container_width=True,
        hide_index=True,
        height=600
    )


    # =====================================================
    # BIỂU ĐỒ THEO NGÀY
    # =====================================================

    st.subheader(
        "📈 Biểu đồ theo ngày"
    )


    daily_chart = (
        daily_df.copy()
    )


    daily_chart["Ngày"] = (
        pd.to_datetime(
            daily_chart[
                "Ngày"
            ],
            format="%d/%m/%Y"
        )
    )


    daily_chart = (
        daily_chart.set_index(
            "Ngày"
        )
    )


    st.line_chart(
        daily_chart[
            [
                "Doanh thu",
                "Chi phí",
                "Thực thu"
            ]
        ]
    )
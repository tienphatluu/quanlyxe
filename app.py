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

# Tài khoản được phép truy cập website.
USERS = {
    "admin": ADMIN_PASSWORD,
    "nhanvien": "123456",
}


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

if "website_logged_in" not in st.session_state:
    st.session_state.website_logged_in = False

if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if "security_action" not in st.session_state:
    st.session_state.security_action = None

if "last_security_action" not in st.session_state:
    st.session_state.last_security_action = None


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
# BẢO MẬT
# =========================================================

def require_admin(action_name):
    st.session_state.security_action = action_name
    st.rerun()


def security_dialog():
    action = st.session_state.get("security_action")
    if not action:
        return True

    st.warning(f"🔐 Thao tác **{action}** yêu cầu mật khẩu Admin.")
    with st.form("security_confirm_form"):
        password = st.text_input("Mật khẩu Admin", type="password")
        c1, c2 = st.columns(2)
        with c1:
            ok = st.form_submit_button("🔓 Xác nhận", type="primary", use_container_width=True)
        with c2:
            cancel = st.form_submit_button("Hủy", use_container_width=True)
        if cancel:
            st.session_state.security_action = None
            st.rerun()
        if ok:
            if password == ADMIN_PASSWORD:
                st.session_state.last_security_action = action
                st.session_state.security_action = None
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("❌ Mật khẩu Admin không đúng.")
    return False


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
    """
    Trạng thái theo ngày, ưu tiên khách mới nếu có khách mới thuê
    trong cùng ngày; nếu không có khách mới thì ưu tiên "Đã trả".

    Ví dụ:
    - Khách A: 02/08 -> 03/08, trạng thái Đã trả
      => ngày 03/08: Đã trả.
    - Nếu ngày 03/08 có khách B bắt đầu thuê và đang thuê
      => ngày 03/08: Đang thuê.
    - Nếu khách thuê và trả trong chính ngày đó, trạng thái là Đã trả
      khi đơn đó đã được nhập là "Đã trả".
    """

    rentals = get_rentals()

    if rentals.empty:
        return "Đang rảnh", 0, None

    car_rentals = []

    for _, row in rentals.iterrows():

        if int(row["car_id"]) != int(car_id):
            continue

        tu = parse_date(row["tu_ngay"])
        den = parse_date(row["den_ngay"])

        if tu <= day <= den:
            car_rentals.append((tu, den, row))

    if not car_rentals:
        return "Đang rảnh", 0, None

    # 1. Có khách mới bắt đầu trong ngày và đang thuê:
    # xe tiếp tục được tính là đang thuê.
    new_active = [
        item for item in car_rentals
        if item[0] == day
        and item[2]["trang_thai"] == "Đang thuê"
    ]

    if new_active:
        item = new_active[-1]
        return "Đang thuê", item[2]["tien_thue"], item[2]

    # 2. Nếu không có khách mới đang thuê, ưu tiên ĐÃ TRẢ.
    # Bao gồm cả trường hợp thuê và trả trong cùng ngày.
    returned_today = [
        item for item in car_rentals
        if item[2]["trang_thai"] == "Đã trả"
        and item[1] == day
    ]

    if returned_today:
        item = returned_today[-1]
        return "Đã trả", item[2]["tien_thue"], item[2]

    # 3. Đơn bắt đầu trong ngày nhưng đã trả ngay trong ngày.
    returned_started_today = [
        item for item in car_rentals
        if item[0] == day
        and item[2]["trang_thai"] == "Đã trả"
    ]

    if returned_started_today:
        item = returned_started_today[-1]
        return "Đã trả", item[2]["tien_thue"], item[2]

    # 4. Đơn đang thuê bao phủ ngày.
    active = [
        item for item in car_rentals
        if item[2]["trang_thai"] == "Đang thuê"
    ]

    if active:
        item = active[-1]
        return "Đang thuê", item[2]["tien_thue"], item[2]

    # 5. Các trạng thái còn lại.
    returned = [
        item for item in car_rentals
        if item[2]["trang_thai"] == "Đã trả"
    ]

    if returned:
        item = returned[-1]
        return "Đã trả", item[2]["tien_thue"], item[2]

    return "Đang rảnh", 0, None



# =========================================================
# ĐĂNG NHẬP WEBSITE
# =========================================================

if not st.session_state.website_logged_in:
    st.title("🔐 Quản lý xe cho thuê")
    st.subheader("Đăng nhập hệ thống")
    with st.form("website_login_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        login = st.form_submit_button("🔓 Đăng nhập", type="primary", use_container_width=True)
        if login:
            if username in USERS and USERS[username] == password:
                st.session_state.website_logged_in = True
                st.session_state.current_user = username
                st.session_state.admin_logged_in = username == "admin"
                st.rerun()
            else:
                st.error("❌ Tài khoản hoặc mật khẩu không đúng.")
    st.info("🔒 Chỉ tài khoản được cấp quyền mới có thể truy cập hệ thống.")
    st.stop()

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("🛵 QUẢN LÝ XE")
st.sidebar.success(f"👤 {st.session_state.current_user}")
if st.sidebar.button("🚪 Đăng xuất", key="website_logout"):
    st.session_state.website_logged_in = False
    st.session_state.current_user = None
    st.session_state.admin_logged_in = False
    st.session_state.security_action = None
    st.session_state.last_security_action = None
    st.rerun()

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

    st.title("🛵 Quản lý xe")

    if not security_dialog():
        st.stop()

    action = st.session_state.pop("last_security_action", None)

    if action == "thêm xe":
        pending = st.session_state.pop("pending_car", None)
        if pending:
            if add_car(pending["bien_so"], pending["ten_xe"], pending["gia_ngay"]):
                st.success(f"✅ Đã thêm xe {pending['bien_so']} thành công!")
                st.rerun()
            else:
                st.error("❌ Biển số này đã tồn tại.")

    elif action and action.startswith("xóa xe "):
        pending = st.session_state.pop("pending_delete_car", None)
        if pending:
            delete_car(pending["id"])
            st.success(f"✅ Đã xóa xe {pending['bien_so']}.")
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
            st.error("❌ Vui lòng nhập biển số.")
        elif not ten_xe.strip():
            st.error("❌ Vui lòng nhập tên xe.")
        else:
            st.session_state.pending_car = {
                "bien_so": bien_so,
                "ten_xe": ten_xe,
                "gia_ngay": gia_ngay
            }
            require_admin("thêm xe")

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
                    st.session_state.pending_delete_car = {
                        "id": int(car["id"]),
                        "bien_so": str(car["bien_so"])
                    }
                    require_admin(f"xóa xe {car['bien_so']}")


# =========================================================
# TRANG ĐƠN THUÊ
# =========================================================

elif page == "📋 Đơn thuê":

    st.title(
        "📋 Quản lý đơn thuê"
    )

    if not security_dialog():
        st.stop()

    action = st.session_state.pop("last_security_action", None)
    if action and action.startswith("xóa đơn #"):
        pending_id = st.session_state.pop("pending_delete_rental", None)
        if pending_id is not None:
            delete_rental(pending_id)
            st.success(f"✅ Đã xóa đơn #{pending_id}.")
            st.rerun()


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
            st.session_state.pending_delete_rental = int(rental_id)
            require_admin(f"xóa đơn #{rental_id}")


# =========================================================
# TRANG CHI PHÍ
# =========================================================

elif page == "🔧 Chi phí / Khấu hao":

    st.title(
        "🔧 Chi phí / Khấu hao"
    )

    if not security_dialog():
        st.stop()

    action = st.session_state.pop("last_security_action", None)
    if action and action.startswith("xóa chi phí #"):
        pending_id = st.session_state.pop("pending_delete_expense", None)
        if pending_id is not None:
            delete_expense(pending_id)
            st.success(f"✅ Đã xóa chi phí #{pending_id}.")
            st.rerun()


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
            st.session_state.pending_delete_expense = int(expense_id)
            require_admin(f"xóa chi phí #{expense_id}")


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
    # DOANH THU THEO NGÀY - DẠNG LỊCH XE
    # =====================================================

    st.divider()

    st.header(
        f"📅 Doanh thu theo ngày - Tháng {month}/{year}"
    )

    cars = get_cars()
    rentals = get_rentals()
    expenses = get_expenses()

    days_in_month = calendar.monthrange(
        year,
        month
    )[1]

    # -----------------------------------------------------
    # BẢNG GIỐNG LỊCH XE:
    # Mỗi hàng = 1 xe
    # Mỗi cột = 1 ngày
    # Cột cuối = tổng doanh thu của xe trong tháng
    # -----------------------------------------------------

    revenue_table = []

    if not cars.empty:

        for _, car in cars.iterrows():

            row = {
                "Xe":
                    f"{car['bien_so']} - {car['ten_xe']}"
            }

            car_month_total = 0

            for day in range(
                1,
                days_in_month + 1
            ):

                current_day = date(
                    year,
                    month,
                    day
                )

                day_revenue = 0
                day_expense = 0

                if not rentals.empty:

                    car_rentals = rentals[
                        rentals["car_id"] == car["id"]
                    ]

                    for _, rental in car_rentals.iterrows():

                        tu = parse_date(
                            rental["tu_ngay"]
                        )

                        den = parse_date(
                            rental["den_ngay"]
                        )

                        # Doanh thu chỉ ghi nhận ngày bắt đầu
                        if tu == current_day:

                            day_revenue += float(
                                rental["tien_thue"]
                            )

                if not expenses.empty:

                    car_expenses = expenses[
                        expenses["car_id"] == car["id"]
                    ]

                    for _, expense in car_expenses.iterrows():

                        expense_date = parse_date(
                            expense["ngay"]
                        )

                        if expense_date == current_day:

                            day_expense += float(
                                expense["so_tien"]
                            )

                # Doanh thu trong ô ngày
                # Chỉ hiển thị tiền nếu có phát sinh
                if day_revenue > 0:

                    row[
                        str(day)
                    ] = format_money(
                        day_revenue
                    )

                else:

                    row[
                        str(day)
                    ] = "-"

                car_month_total += day_revenue

            # -------------------------------------------------
            # CỘT CUỐI: TỔNG DOANH THU CỦA XE
            # -------------------------------------------------

            row[
                "Tổng"
            ] = format_money(
                car_month_total
            )

            revenue_table.append(
                row
            )

    revenue_calendar_df = pd.DataFrame(
        revenue_table
    )

    st.subheader(
        f"💰 Doanh thu từng xe theo ngày - Tháng {month}/{year}"
    )

    if revenue_calendar_df.empty:

        st.info(
            "Chưa có xe nào."
        )

    else:

        st.dataframe(
            revenue_calendar_df,
            use_container_width=True,
            hide_index=True,
            height=550
        )

    st.caption(
        "💡 Mỗi ô là doanh thu phát sinh của xe trong ngày đó. "
        "Cột **Tổng** là tổng doanh thu của từng xe trong tháng. "
        "Doanh thu đơn thuê chỉ ghi nhận vào ngày bắt đầu thuê."
    )

    # -----------------------------------------------------
    # TỔNG DOANH THU THEO NGÀY - TẤT CẢ XE
    # -----------------------------------------------------

    st.subheader(
        f"📊 Tổng doanh thu tất cả xe theo ngày - Tháng {month}/{year}"
    )

    daily_total_row = {
        "Ngày": "Tổng tất cả xe"
    }

    grand_total = 0

    for day in range(
        1,
        days_in_month + 1
    ):

        current_day = date(
            year,
            month,
            day
        )

        total_day_revenue = 0

        if not rentals.empty:

            for _, rental in rentals.iterrows():

                tu = parse_date(
                    rental["tu_ngay"]
                )

                if tu == current_day:

                    total_day_revenue += float(
                        rental["tien_thue"]
                    )

        grand_total += total_day_revenue

        daily_total_row[
            "Ngày " + str(day)
        ] = (
            format_money(
                total_day_revenue
            )
            if total_day_revenue > 0
            else "-"
        )

    daily_total_row[
        "Tổng tháng"
    ] = format_money(
        grand_total
    )

    daily_total_df = pd.DataFrame(
        [daily_total_row]
    )

    st.dataframe(
        daily_total_df,
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------------------------
    # KPI THÁNG
    # -----------------------------------------------------

    total_expense_month = 0

    if not expenses.empty:

        for _, expense in expenses.iterrows():

            expense_date = parse_date(
                expense["ngay"]
            )

            if (
                expense_date.year == year
                and
                expense_date.month == month
            ):

                total_expense_month += float(
                    expense["so_tien"]
                )

    net_month = (
        grand_total
        -
        total_expense_month
    )

    k1, k2, k3 = st.columns(3)

    k1.metric(
        "💰 Tổng doanh thu tháng",
        format_money(
            grand_total
        )
    )

    k2.metric(
        "🔧 Chi phí tháng",
        format_money(
            total_expense_month
        )
    )

    k3.metric(
        "💵 Doanh thu thực tế",
        format_money(
            net_month
        )
    )

    # -----------------------------------------------------
    # BẢNG CHI TIẾT ĐƠN THUÊ BÊN DƯỚI
    # -----------------------------------------------------

    st.subheader(
        "📋 Chi tiết đơn thuê phát sinh trong tháng"
    )

    if not rentals.empty:

        month_rentals = rentals.copy()

        month_rentals[
            "_tu"
        ] = pd.to_datetime(
            month_rentals[
                "tu_ngay"
            ]
        )

        month_rentals = month_rentals[
            (
                month_rentals["_tu"].dt.year == year
            )
            &
            (
                month_rentals["_tu"].dt.month == month
            )
        ]

        if month_rentals.empty:

            st.info(
                "Không có đơn thuê phát sinh trong tháng."
            )

        else:

            detail_df = month_rentals[
                [
                    "bien_so",
                    "ten_xe",
                    "tu_ngay",
                    "den_ngay",
                    "trang_thai",
                    "tien_thue"
                ]
            ].copy()

            detail_df = detail_df.rename(
                columns={
                    "bien_so": "Biển số",
                    "ten_xe": "Tên xe",
                    "tu_ngay": "Từ ngày",
                    "den_ngay": "Đến ngày",
                    "trang_thai": "Trạng thái",
                    "tien_thue": "Doanh thu"
                }
            )

            detail_df[
                "Doanh thu"
            ] = detail_df[
                "Doanh thu"
            ].apply(
                format_money
            )

            st.dataframe(
                detail_df,
                use_container_width=True,
                hide_index=True
            )

    # =====================================================
    # BIỂU ĐỒ DOANH THU THEO NGÀY
    # =====================================================

    st.subheader(
        "📈 Biểu đồ tổng doanh thu theo ngày"
    )

    chart_rows = []

    for day in range(
        1,
        days_in_month + 1
    ):

        current_day = date(
            year,
            month,
            day
        )

        total_day_revenue = 0

        if not rentals.empty:

            for _, rental in rentals.iterrows():

                tu = parse_date(
                    rental["tu_ngay"]
                )

                if tu == current_day:

                    total_day_revenue += float(
                        rental["tien_thue"]
                    )

        chart_rows.append(
            {
                "Ngày":
                    current_day,
                "Doanh thu":
                    total_day_revenue
            }
        )

    chart_df = pd.DataFrame(
        chart_rows
    )

    if not chart_df.empty:

        chart_df = chart_df.set_index(
            "Ngày"
        )

        st.line_chart(
            chart_df[
                "Doanh thu"
            ]
        )



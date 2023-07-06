import plotly.graph_objects as go
import io
import pandas as pd
import mplfinance as mpf


def chart(candles_data):
    """
    Tạo biểu đồ nến (candlestick chart) từ dữ liệu nến và trả về dưới dạng buffer.

    Tham số:
    - candles_data (list[list]): Dữ liệu nến, mỗi phần tử là một danh sách gồm các giá trị:
        [Thời gian, Giá mở cửa, Giá cao nhất, Giá thấp nhất, Giá đóng cửa, Khối lượng giao dịch].

    Trả về:
    - buffer (io.BytesIO): Đối tượng buffer chứa dữ liệu hình ảnh của biểu đồ nến.
    """

    # Chuyển dữ liệu thành một DataFrame
    df = pd.DataFrame(
        candles_data, columns=["Time", "Open", "High", "Low", "Close", "Volume"]
    )

    # Chuyển đổi Unix timestamp thành định dạng datetime
    df["Time"] = pd.to_datetime(df["Time"], unit="ms")

    # Thiết lập cột Time làm chỉ mục cho DataFrame
    df.set_index("Time", inplace=True)

    # Vẽ biểu đồ nến (candlestick chart)
    buffer = io.BytesIO()
    mpf.plot(
        df,
        type="candle",
        volume=True,
        style="yahoo",
        savefig=dict(fname=buffer, bbox_inches="tight"),
        datetime_format="%d/%m/%Y %H:%M",
    )
    buffer.seek(0)

    return buffer


def table_to_image(table_data, table_header):
    """
    Chuyển đổi dữ liệu bảng thành hình ảnh và trả về dưới dạng bytes.

    Tham số:
    - table_data (list[tuple]): Dữ liệu trong bảng, mỗi phần tử là một hàng trong bảng.
    - table_header (list): Tiêu đề của bảng, mỗi phần tử tương ứng với tiêu đề một cột trong bảng.

    Trả về:
    - buffer (io.BytesIO): Đối tượng buffer chứa dữ liệu hình ảnh của bảng.
    """

    # cấu hình chiều cao của cell
    cell_height = 25

    # Vẽ bảng
    header = dict(values=table_header, height=cell_height)
    cells = dict(values=list(zip(*table_data)), align="center", height=cell_height)

    go_table = go.Table(header=header, cells=cells)

    fig = go.Figure(
        go_table,
        layout=dict(
            margin=dict(l=0, r=0, t=0, b=0),
        ),
    )

    # tính chiều cao của hình bằng "chiều cao của cell" * ("số dòng" + "header")
    buffer = io.BytesIO()
    fig.write_image(buffer, height=(len(table_data) + 1) * cell_height)
    buffer.seek(0)

    return buffer

import aiofiles
from datetime import datetime
import re
import json
import pytz
from discord.ext.commands import Context


async def read_file_async(file_path):
    """
    Đọc file dạng async.

    Tham số:
        file_path (str): Đường dẫn đến file cần đọc.

    Trả về:
        Chuỗi rỗng khi có lỗi xảy ra.
        Ngược lại trả về nội dung tập tin.

    Thông báo:
        Báo lỗi khi không tìm thấy file hoặc không đọc được file.
    """
    try:
        async with aiofiles.open(file_path, mode="r") as file:
            contents = await file.read()
    except FileNotFoundError:
        print(f"{file_path} không tìm thấy.")
        return None
    except IOError:
        print(f"Lỗi đọc file: {file_path}")
        return None
    else:
        return contents


def verify_object_key(key, object):
    """
    Xác minh xem một khóa có hợp lệ hay không.

    Tham số:
        key (str): Khoá cần xác minh.
        object: Đối tượng bị xác minh.

    Trả về:
        bool: True nếu khóa hợp lệ, False nếu ngược lại.
    """

    if key.lower() in object.keys():
        return True

    return False


async def get_file_content(filename):
    map = {
        "manual": "./assets/manual.json",
        "timeframes": "./assets/timeframes.json",
        "symbols": "./assets/symbols_map.json",
        "messages": "./assets/messages.json",
    }

    if filename not in map.keys():
        print(f"File path {filename} doesn't found.")
        return ""

    file_content = await read_file_async(map.get(filename))

    return json.loads(file_content)


async def verify_symbol(symbol):
    """
    Xác minh xem một ký hiệu (symbol) có hợp lệ hay không.

    Tham số:
        symbol (str): Ký hiệu cần xác minh.

    Trả về:
        bool: True nếu ký hiệu hợp lệ, False nếu ngược lại.
    """
    obj = await get_file_content("symbols")

    return verify_object_key(symbol, obj)


async def verify_command(command):
    """
    Xác minh xem một command có hợp lệ hay không.

    Tham số:
        command (str): Command cần xác minh.

    Trả về:
        bool: True nếu ký hiệu hợp lệ, False nếu ngược lại.
    """
    obj = await get_file_content("manual")

    return verify_object_key(command, obj)


def verify_alert_condition(string):
    """
    Xác minh xem điều kiện của cảnh báo có hợp lệ không.

    Tham số:
        string (str): Chuỗi cần xác minh.

    Trả về:
        Giá trị phù hợp với mẫu cho trước nếu khớp.
        Trả về None nếu không khớp.
    """
    condition_pattern = r"^((==)|(!=)|(<=)|(>=)|(<)|(>))\d*\.?\d*$"

    return re.match(condition_pattern, string)


def evaluate_strings(a, b):
    try:
        result = eval(f"{a} {b}")
    except Exception as err:
        result = False
    return result


def parse_string_to_datetime(str):
    return datetime.strptime(str, "%Y-%m-%dT%H:%M:%S%z")


def format_datetime_to_local(date):
    local_timezone = pytz.timezone("Asia/Ho_Chi_Minh")
    return date.astimezone(local_timezone).strftime("%d/%m/%Y %H:%M")


def get_current_time():
    # lấy thời gian hiện tại theo định dạng dd/mm/yyyy hh:mm
    return format_datetime_to_local(datetime.now())


async def get_message(message_type):
    obj = await get_file_content("messages")

    type_exists = verify_object_key(message_type, obj)

    if type_exists:
        return obj.get(message_type)
    else:
        print(f"get_message: {message_type} doesn't found.")
        return ""

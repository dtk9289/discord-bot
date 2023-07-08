from discord import Intents, File
from discord.ext.commands import Context, Bot, errors
import re
import asyncio
from datetime import datetime

## custom modules
import services
import utils
import visualizers

BOT_TOKEN = "MTEyMjM5MjQyNTE2ODY1NDM2MA.GbYROU.vVGfMiZwfEaQ0SsC_LatLxTKJhHEW3qIcUJ5Jo"

bot = Bot(command_prefix="!", help_command=None, intents=Intents.all())


background_tasks = []


async def _cleanup_finished_tasks(interval):
    while True:
        for task in background_tasks:
            if task.done():
                background_tasks.remove(task)

        await asyncio.sleep(interval)


@bot.event
async def on_ready():
    # sự kiện được kích hoạt sau khi client kết nối được Discord Server
    asyncio.create_task(_cleanup_finished_tasks(30))
    print(f"{bot.user.name} has connected to Discord!")


@bot.event
async def on_command_error(context: Context, error):
    if isinstance(error, errors.CommandNotFound):
        await context.send(await utils.get_message("invalid_command"))

    else:
        print(error)


# tên hàm tương ứng với tên lệnh khi người dùng nhập vào
@bot.command()
async def print_tasks(context: Context):
    for task in background_tasks:
        print(task)


@bot.command()
async def tech_summary(context: Context, symbol_string=""):
    waiting_mesg = await context.send("Please wait!")

    symbols_arr = (
        symbol_string.split(",")
        if symbol_string
        else ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"]
    )
    response = await services.get_technical_summary(symbols_arr)

    if not response:
        await context.send(await utils.get_message("retrieving_data_error"))
        return

    table_data = []
    table_header = ["Symbol", "5MIN", "15MIN", "1HOUR", "1DAY"]
    for symbol, values in response.items():
        table_data.append(
            (
                symbol,
                values["5MIN"],
                values["15MIN"],
                values["1HOUR"],
                values["1DAY"],
            )
        )

    buffer = visualizers.table_to_image(
        table_data=table_data,
        table_header=table_header,
    )

    await waiting_mesg.delete()
    await context.send(
        file=File(buffer, filename="image.png"),
        content=f"{context.author.mention} Tổng kết kỹ thuật ({utils.get_current_time()})",
    )


@bot.command()
async def sentiment(context: Context, symbol_string=""):
    waiting_mesg = await context.send("Please wait!")

    symbols = (
        symbol_string.split(",")
        if symbol_string != ""
        else ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF"]
    )

    response = await services.get_sentiment(symbols=symbols)

    if not response:
        await waiting_mesg.delete()
        await context.send(
            await utils.get_message("retrieving_data_error"),
        )
        return

    # tạo table để chuyển thành image
    table_data = []
    table_header = ("Symbol", "Type", "Position", "Percentage", "Volume (lots)")
    for symbol, values in response.items():
        short_pos = values["Short"]["Positions"]
        short_percentage = values["Short"]["Percentage"]
        short_vol = values["Short"]["Volume(lots)"]
        table_data.append((symbol, "Short", short_pos, short_percentage, short_vol))

        long_pos = values["Long"]["Positions"]
        long_percentage = values["Long"]["Percentage"]
        long_vol = values["Long"]["Volume(lots)"]
        table_data.append(("", "Long", long_pos, long_percentage, long_vol))

    image_bytes = visualizers.table_to_image(
        table_data=table_data, table_header=table_header
    )

    await waiting_mesg.delete()
    await context.send(
        file=File(image_bytes, filename="image.png"),
        content=f"{context.author.mention} Độ hưng phấn thị trường ({utils.get_current_time()})",
    )


@bot.command()
async def news(context: Context, symbol=""):
    valid_symbol = await utils.verify_symbol(symbol)
    working_mesg = await context.send("Please wait!")

    if valid_symbol:
        response = await services.get_symbol_news(symbol)

    elif not symbol:
        response = await services.get_news()

    else:
        await working_mesg.delete()
        await context.send(await utils.get_message("invalid_argument"))
        return

    if not response:
        await working_mesg.delete()
        await context.send(await utils.get_message("retrieving_data_error"))
        return

    contents = []
    str = ""
    for i in range(len(response)):
        if valid_symbol:
            str += f"{i+1}. {response[i]['title']}\n<{response[i]['url']}>\n"

        else:
            str += f"{i+1}. {response[i]['title']} - {response[i]['date']}\n<{response[i]['url']}>\n"

        # tách dữ liệu cần gửi thành nhiều phần do giới hạn của tài khoản free
        if (i + 1) % 5 == 0 or i + 1 == len(response):
            contents.append(str)
            str = ""

    await working_mesg.delete()
    for content in contents:
        await context.send(content)


@bot.command()
async def chart(
    context: Context,
    symbol="XAUUSD",
    timeframe="1HOUR",
    quantity=30,
):
    waiting_mesg = await context.send("Please wait!")

    valid_symbol = await utils.verify_symbol(symbol)
    if not valid_symbol:
        await waiting_mesg.delete()
        await context.send(
            await utils.get_message("invalid_argument"),
        )
        return

    candles = await services.get_candles(
        symbol=symbol,
        timeframe=timeframe,
        quantity=quantity,
        time_direction="P",
        epoch_time=0,
    )

    if not len(candles) > 0:
        await waiting_mesg.delete()
        await context.send(await utils.get_message("retrieving_data_error"))
        return

    image_bytes = visualizers.chart(candles)

    await waiting_mesg.delete()
    await context.send(
        file=File(image_bytes, filename="image.png"),
        content=f"{context.author.mention} {symbol} {timeframe} {utils.get_current_time()}",
    )


@bot.command()
async def timeframes(context: Context):
    data = await utils.get_file_content("timeframes")
    keys = list(data.keys())
    timeframes_string = ", ".join(keys)
    await context.send(
        f"{context.author.mention}\n **Các mốc thời gian được hỗ trợ, dùng cho lệnh !chart**\n{timeframes_string}"
    )


@bot.command()
async def symbols(context: Context, search_text=""):
    data = await utils.get_file_content("symbols")

    keys = list(data.keys())

    search_pattern = rf"(\w+)?{search_text}(\w+)?"
    filtered_keys = [key for key in keys if re.match(search_pattern, key)]

    symbols_string = ", ".join(filtered_keys)
    await context.send(f"{symbols_string}")


@bot.command()
async def alert(context: Context, symbol="", condition=""):
    supported_symbol = await utils.verify_symbol(symbol.lower())
    valid_condition = utils.verify_alert_condition(condition)

    if supported_symbol and valid_condition:

        async def price_monitoring(interval):
            while True:
                candles = await services.get_candles(symbol, "TICK", 1, "P", 0)
                try:
                    price = candles[0][1]
                except Exception as err:
                    print("price_monitoring" + err)
                    continue

                if utils.evaluate_strings(price, condition):
                    await context.send(
                        f"{context.author.mention} {symbol.upper()} thỏa mãn điều kiện {condition}, giá hiện tại {price}"
                    )
                    return

                await asyncio.sleep(interval)

        task = bot.loop.create_task(price_monitoring(5))
        background_tasks.append(task)

    else:
        await context.send(await utils.get_message("invalid_argument"))


@bot.command()
async def help(context: Context, command=""):
    manual_data = await utils.get_file_content("manual")

    if not command:
        manual_text = "\n".join(
            [f"{cmd}: {details['description']}" for cmd, details in manual_data.items()]
        )

    else:
        command_details = manual_data.get(command)

        if not command_details:
            await context.send(await utils.get_message("invalid_command"))
            return

        description = command_details.get("description")
        usage = command_details.get("usage")
        example = command_details.get("example")
        manual_text = f"Chức năng: {description}\nCú pháp: {usage}\nVí dụ: {example}"

    await context.send(manual_text)


bot.run(BOT_TOKEN)

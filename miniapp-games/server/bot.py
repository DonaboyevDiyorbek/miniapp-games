"""Telegram bot: /start va menyu tugmasi Mini App ni ochadi.  Ishga tushirish: python -m server.bot"""
import asyncio, os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message, WebAppInfo


async def main():
    bot, dp, url = Bot(os.environ["BOT_TOKEN"]), Dispatcher(), os.environ["WEBAPP_URL"]

    @dp.message(CommandStart())
    async def start(m: Message):
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🎮 O'ynash", web_app=WebAppInfo(url=url))]])
        await m.answer("O'yinlar to'plamiga xush kelibsiz! 👇", reply_markup=kb)

    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="O'yinlar", web_app=WebAppInfo(url=url)))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

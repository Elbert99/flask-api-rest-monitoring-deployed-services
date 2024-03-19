import asyncio
import time
import requests
import telegram
import os
import json

from flask.cli import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

load_dotenv()


class ServiceMonitor:
    def __init__(self):
        self.services = json.loads(os.getenv('SERVICES'))
        self.bot = telegram.Bot(token=os.getenv('TELEGRAM_API_BOT_TOKEN'))
        self.chat_id = None
        self.received_first_start_command = False
        self.outside_flag = True
        self.outside_flag2 = True
        self.down_services = []
        self.up_services = []

    def start_command(self, update: Update, _: CallbackContext) -> None:
        self.chat_id = update.effective_chat.id
        self.received_first_start_command = True
        user = update.effective_user
        self.bot.send_message(chat_id=self.chat_id, text=f'Hello {user.full_name}!. Welcome to a Python Flask Service '
                                                         f'for '
                                                         f'monitoring other services.')

    def start_bot(self):
        updater = Updater(os.getenv('TELEGRAM_API_BOT_TOKEN'))
        dispatcher = updater.dispatcher
        dispatcher.add_handler(CommandHandler("start", self.start_command))
        # Initialize bot
        updater.start_polling()
        # Wait for bot closure
        while not self.received_first_start_command:
            time.sleep(1)
        # Stop the bot after receiving the very first /start command
        updater.stop()
        print("Bot stopped after receiving the very first /start command")

    async def check_services(self):
        message_send_once = False
        up_services_temp = []
        for address, port, service_name in self.services:
            url = f'{address}:{port}'
            try:
                if requests.get(url, timeout=7).status_code == 200:
                    print(f'The service: {service_name} ({url}) IS UP')
                    up_services_temp.append({'service_name': service_name, 'url': url})
            except requests.exceptions.ConnectionError:
                print('ConnectionError')
                message_send_once = True
                self.down_services.append({'service_name': service_name, 'url': url})

        self.up_services = up_services_temp
        if len(self.up_services) == 3:
            service_info = ' '.join(
                [f"-{service['service_name']} ({service['url']})\n" for service in self.up_services])
            self.bot.send_message(chat_id=self.chat_id,
                                  text=f'All services were successfully restored\n-->Services:\n {service_info}\n '
                                       f'ARE UP.')

        return message_send_once

    async def send_message(self, services):
        if len(services) > 1:
            service_info = ' '.join(
                [f"-{service['service_name']} ({service['url']})\n" for service in self.down_services])
            self.bot.send_message(chat_id=self.chat_id, text=f'The services:\n {service_info}\n ARE DOWN.')
        elif len(services):
            service_info = ' '.join(
                [f"-{service['service_name']} ({service['url']})\n" for service in self.down_services])
            self.bot.send_message(chat_id=self.chat_id, text=f'The service: {service_info} IS DOWN.')

    def start_monitoring(self):
        self.start_bot()
        while True:
            if self.chat_id is not None:
                message_send_once = asyncio.run(self.check_services())
                if len(self.down_services) == 1:
                    if message_send_once and self.outside_flag:
                        asyncio.run(self.send_message(self.down_services))
                        self.outside_flag = False
                    self.down_services.clear()
                else:
                    self.outside_flag = True
                    if message_send_once and self.outside_flag and self.outside_flag2:
                        asyncio.run(self.send_message(self.down_services))
                        self.outside_flag2 = False
                    self.down_services.clear()

            time.sleep(60)

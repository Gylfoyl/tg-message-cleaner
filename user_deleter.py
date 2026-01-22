import asyncio
import logging
import os
import glob
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerUser, InputPeerChat, InputPeerChannel
from telethon import errors
import time
from config import API_ID, API_HASH

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class UserMessageDeleter:
    def __init__(self):
        self.client = TelegramClient('user_session', API_ID, API_HASH)
        self.is_running = False
        
    async def cleanup_sessions(self):
        """Удаление сессионных файлов"""
        try:
            # Закрываем клиент перед удалением сессии
            if self.client.is_connected():
                await self.client.disconnect()
            
            # Ищем и удаляем сессионные файлы
            session_files = glob.glob('user_session*')
            for session_file in session_files:
                try:
                    os.remove(session_file)
                    print(f"🗑️ Удален файл сессии: {session_file}")
                except Exception as e:
                    print(f"⚠️ Не удалось удалить {session_file}: {e}")
                    
        except Exception as e:
            print(f"⚠️ Ошибка при очистке сессий: {e}")
        
    async def start(self):
        """Запуск клиента"""
        print("🚀 Запуск клиента Telegram...")
        await self.client.start()
        print("✅ Успешный вход в аккаунт!")
        
        # Получаем информацию о пользователе
        me = await self.client.get_me()
        print(f"👤 Привет, {me.first_name}!")
        
        # Показываем меню
        await self.show_main_menu()
    
    async def show_main_menu(self):
        """Главное меню"""
        print("\n" + "="*50)
        print("📋 Меню удаления сообщений:")
        print("1. Показать все чаты (группы, каналы, личные)")
        print("2. Удалить сообщения в конкретной группе")
        print("3. Удалить сообщения во всех группах")
        print("4. Удалить личные сообщения")
        print("5. Выход")
        print("="*50)
        
        choice = input("Выберите опцию (1-5): ").strip()
        
        if choice == "1":
            await self.show_all_chats()
        elif choice == "2":
            await self.delete_in_specific_group()
        elif choice == "3":
            await self.delete_in_all_groups()
        elif choice == "4":
            await self.delete_private_messages()
        elif choice == "5":
            print("👋 До свидания!")
            print("🧹 Очистка сессионных файлов...")
            await self.cleanup_sessions()
            return
        else:
            print("❌ Неверный выбор. Попробуйте снова.")
            await self.show_main_menu()
    
    async def show_all_chats(self):
        """Показать все чаты пользователя"""
        print("\n🔍 Поиск всех чатов...")
        
        dialogs = await self.client.get_dialogs()
        all_chats = []
        
        for dialog in dialogs:
            chat_info = {
                'name': dialog.title,
                'id': dialog.id,
                'entity': dialog.entity,
                'type': 'user' if dialog.is_user else 'channel' if dialog.is_channel else 'group'
            }
            all_chats.append(chat_info)
        
        if not all_chats:
            print("❌ Чаты не найдены.")
            await self.show_main_menu()
            return
        
        print(f"\n📋 Найдено {len(all_chats)} чатов:")
        print("-" * 60)
        
        for i, chat in enumerate(all_chats, 1):
            icon = "👤" if chat['type'] == 'user' else "📢" if chat['type'] == 'channel' else "👥"
            chat_type = "Личный" if chat['type'] == 'user' else "Канал" if chat['type'] == 'channel' else "Группа"
            print(f"{i:3d}. {icon} {chat['name']}")
            print(f"      Тип: {chat_type} | ID: {chat['id']}")
        
        print("-" * 60)
        
        # Сохраняем чаты для дальнейшего использования
        self.all_chats = all_chats
        
        choice = input(f"\nВыберите номер чата для удаления сообщений (1-{len(all_chats)}) или 0 для возврата: ").strip()
        
        try:
            chat_num = int(choice)
            
            if chat_num == 0:
                await self.show_main_menu()
                return
            
            if 1 <= chat_num <= len(all_chats):
                selected_chat = all_chats[chat_num - 1]
                await self.delete_messages_in_chat(selected_chat)
            else:
                print("❌ Неверный выбор.")
                await self.show_all_chats()
                
        except ValueError:
            print("❌ Введите число.")
            await self.show_all_chats()
    
    async def delete_messages_in_chat(self, chat):
        """Удаление сообщений в указанном чате"""
        print(f"\n🔍 Поиск ваших сообщений в чате: {chat['name']}")
        
        try:
            # Получаем все сообщения
            messages = []
            limit = 10000
            
            async for message in self.client.iter_messages(chat['entity'], limit=limit):
                if message.out:  # Только исходящие сообщения
                    messages.append(message)
            
            if not messages:
                print("✅ Ваши сообщения не найдены.")
                await self.show_main_menu()
                return 0
            
            print(f"📝 Найдено {len(messages)} ваших сообщений")
            
            confirm = input(f"⚠️ Удалить все {len(messages)} сообщений? (да/нет): ").strip().lower()
            
            if confirm != 'да':
                print("❌ Операция отменена.")
                await self.show_main_menu()
                return 0
            
            # Удаляем сообщения
            deleted_count = 0
            batch_size = 100
            
            print("🔄 Начинаю удаление...")
            
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                message_ids = [msg.id for msg in batch]
                
                try:
                    await self.client.delete_messages(chat['entity'], message_ids)
                    deleted_count += len(batch)
                    
                    progress = (deleted_count / len(messages)) * 100
                    print(f"📊 Прогресс: {deleted_count}/{len(messages)} ({progress:.1f}%)")
                    
                    # Небольшая задержка чтобы избежать FloodWait
                    await asyncio.sleep(1)
                    
                except errors.MessageDeleteForbiddenError:
                    print("❌ Нет прав для удаления некоторых сообщений")
                    break
                except errors.FloodWait as e:
                    print(f"⏰ Слишком много запросов. Ждем {e.seconds} секунд...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"❌ Ошибка при удалении: {e}")
                    break
            
            print(f"✅ Удалено {deleted_count} сообщений в чате {chat['name']}")
            await self.show_main_menu()
            return deleted_count
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await self.show_main_menu()
            return 0
    
    async def show_my_groups(self):
        """Показать все группы и каналы пользователя"""
        print("\n🔍 Поиск ваших групп и каналов...")
        
        dialogs = await self.client.get_dialogs()
        groups = []
        
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                groups.append({
                    'name': dialog.title,
                    'id': dialog.id,
                    'type': 'channel' if dialog.is_channel else 'group',
                    'entity': dialog.entity
                })
        
        if not groups:
            print("❌ Группы и каналы не найдены.")
            await self.show_main_menu()
            return
        
        print(f"\n📋 Найдено {len(groups)} групп/каналов:")
        print("-" * 60)
        
        for i, group in enumerate(groups, 1):
            group_type = "📢 Канал" if group['type'] == 'channel' else "👥 Группа"
            print(f"{i:2d}. {group_type}: {group['name']}")
            print(f"     ID: {group['id']}")
        
        print("-" * 60)
        
        # Сохраняем группы для дальнейшего использования
        self.groups = groups
        
        choice = input("\nНажмите Enter для возврата в главное меню...")
        await self.show_main_menu()
    
    async def delete_in_specific_group(self):
        """Удаление сообщений в конкретной группе"""
        if not hasattr(self, 'groups'):
            print("🔍 Сначала получите список групп...")
            await self.show_my_groups()
            return
        
        print("\n📋 Выберите группу для удаления сообщений:")
        
        for i, group in enumerate(self.groups, 1):
            group_type = "📢" if group['type'] == 'channel' else "👥"
            print(f"{i:2d}. {group_type} {group['name']}")
        
        print(f"{len(self.groups)+1:2d}. 🔙 Назад")
        
        try:
            choice = int(input(f"\nВыберите номер группы (1-{len(self.groups)+1}): ").strip())
            
            if choice == len(self.groups) + 1:
                await self.show_main_menu()
                return
            
            if 1 <= choice <= len(self.groups):
                selected_group = self.groups[choice - 1]
                await self.delete_messages_in_group(selected_group)
            else:
                print("❌ Неверный выбор.")
                await self.delete_in_specific_group()
                
        except ValueError:
            print("❌ Введите число.")
            await self.delete_in_specific_group()
    
    async def delete_private_messages(self):
        """Удаление личных сообщений"""
        print("\n📋 Удаление личных сообщений:")
        print("1. За последние 24 часа")
        print("2. За последнюю неделю")
        print("3. За все время")
        print("4. 🔙 Назад")
        
        choice = input(f"\nВыберите период (1-4): ").strip()
        
        if choice == "4":
            await self.show_main_menu()
            return
        
        # Определяем период в секундах
        import datetime
        now = datetime.datetime.now()
        
        if choice == "1":
            period_hours = 24
            cutoff_time = now - datetime.timedelta(hours=24)
            period_text = "последние 24 часа"
        elif choice == "2":
            period_hours = 24 * 7
            cutoff_time = now - datetime.timedelta(days=7)
            period_text = "последнюю неделю"
        elif choice == "3":
            cutoff_time = None  # Все время
            period_hours = None
            period_text = "все время"
        else:
            print("❌ Неверный выбор.")
            await self.delete_private_messages()
            return
        
        print(f"\n🔍 Поиск личных диалогов...")
        
        # Получаем все диалоги
        dialogs = await self.client.get_dialogs()
        private_chats = []
        
        for dialog in dialogs:
            if dialog.is_user and not dialog.is_bot:  # Только личные чаты с пользователями
                private_chats.append({
                    'name': dialog.title,
                    'id': dialog.id,
                    'entity': dialog.entity
                })
        
        if not private_chats:
            print("❌ Личные диалоги не найдены.")
            await self.show_main_menu()
            return
        
        print(f"📝 Найдено {len(private_chats)} личных диалогов")
        
        # Показываем диалоги для выбора
        print("\nВыберите диалог для очистки:")
        for i, chat in enumerate(private_chats, 1):
            print(f"{i:2d}. 💬 {chat['name']}")
        
        print(f"{len(private_chats)+1:2d}. 🔙 Назад")
        
        try:
            chat_choice = int(input(f"\nВыберите номер диалога (1-{len(private_chats)+1}): ").strip())
            
            if chat_choice == len(private_chats) + 1:
                await self.show_main_menu()
                return
            
            if 1 <= chat_choice <= len(private_chats):
                selected_chat = private_chats[chat_choice - 1]
                await self.delete_private_messages_in_chat(selected_chat, cutoff_time, period_text)
            else:
                print("❌ Неверный выбор.")
                await self.delete_private_messages()
                
        except ValueError:
            print("❌ Введите число.")
            await self.delete_private_messages()
    
    async def delete_private_messages_in_chat(self, chat, cutoff_time, period_text):
        """Удаление личных сообщений в конкретном чате"""
        print(f"\n🔍 Поиск ваших сообщений в диалоге: {chat['name']}")
        print(f"📅 Период: {period_text}")
        
        try:
            # Получаем все сообщения
            messages = []
            limit = 10000
            
            async for message in self.client.iter_messages(chat['entity'], limit=limit):
                if message.out:  # Только исходящие сообщения
                    # Проверяем период
                    if cutoff_time and message.date < cutoff_time:
                        continue
                    messages.append(message)
            
            if not messages:
                print("✅ Ваши сообщения за указанный период не найдены.")
                await self.show_main_menu()
                return 0
            
            print(f"📝 Найдено {len(messages)} ваших сообщений за {period_text}")
            
            confirm = input(f"⚠️ Удалить все {len(messages)} сообщений? (да/нет): ").strip().lower()
            
            if confirm != 'да':
                print("❌ Операция отменена.")
                await self.show_main_menu()
                return 0
            
            # Удаляем сообщения
            deleted_count = 0
            batch_size = 100
            
            print("🔄 Начинаю удаление...")
            
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                message_ids = [msg.id for msg in batch]
                
                try:
                    await self.client.delete_messages(chat['entity'], message_ids)
                    deleted_count += len(batch)
                    
                    progress = (deleted_count / len(messages)) * 100
                    print(f"📊 Прогресс: {deleted_count}/{len(messages)} ({progress:.1f}%)")
                    
                    # Небольшая задержка чтобы избежать FloodWait
                    await asyncio.sleep(1)
                    
                except errors.MessageDeleteForbiddenError:
                    print("❌ Нет прав для удаления некоторых сообщений")
                    break
                except errors.FloodWait as e:
                    print(f"⏰ Слишком много запросов. Ждем {e.seconds} секунд...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"❌ Ошибка при удалении: {e}")
                    break
            
            print(f"✅ Удалено {deleted_count} сообщений в диалоге {chat['name']}")
            await self.show_main_menu()
            return deleted_count
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await self.show_main_menu()
            return 0
    
    async def delete_in_all_groups(self):
        """Удаление сообщений во всех группах"""
        if not hasattr(self, 'groups'):
            print("🔍 Сначала получите список групп...")
            await self.show_my_groups()
            return
        
        confirm = input(f"\n⚠️ Вы уверены, что хотите удалить сообщения во всех {len(self.groups)} группах? (да/нет): ").strip().lower()
        
        if confirm != 'да':
            print("❌ Операция отменена.")
            await self.show_main_menu()
            return
        
        total_deleted = 0
        for group in self.groups:
            print(f"\n🔄 Обработка группы: {group['name']}")
            deleted = await self.delete_messages_in_group(group, show_menu=False)
            total_deleted += deleted
        
        print(f"\n✅ Завершено! Всего удалено сообщений: {total_deleted}")
        await self.show_main_menu()
    
    async def delete_messages_in_group(self, group, show_menu=True):
        """Удаление сообщений в указанной группе"""
        print(f"\n🔍 Поиск ваших сообщений в группе: {group['name']}")
        
        try:
            # Получаем все сообщения
            messages = []
            limit = 10000  # Ограничение для безопасности
            
            async for message in self.client.iter_messages(group['entity'], limit=limit):
                if message.out:  # Только исходящие сообщения (ваши)
                    messages.append(message)
            
            if not messages:
                print("✅ Ваши сообщения не найдены.")
                if show_menu:
                    await self.show_main_menu()
                return 0
            
            print(f"📝 Найдено {len(messages)} ваших сообщений")
            
            confirm = input(f"⚠️ Удалить все {len(messages)} сообщений? (да/нет): ").strip().lower()
            
            if confirm != 'да':
                print("❌ Операция отменена.")
                if show_menu:
                    await self.show_main_menu()
                return 0
            
            # Удаляем сообщения
            deleted_count = 0
            batch_size = 100  # Удаляем пачками
            
            print("🔄 Начинаю удаление...")
            
            for i in range(0, len(messages), batch_size):
                batch = messages[i:i + batch_size]
                message_ids = [msg.id for msg in batch]
                
                try:
                    await self.client.delete_messages(group['entity'], message_ids)
                    deleted_count += len(batch)
                    
                    progress = (deleted_count / len(messages)) * 100
                    print(f"📊 Прогресс: {deleted_count}/{len(messages)} ({progress:.1f}%)")
                    
                    # Небольшая задержка чтобы избежать FloodWait
                    await asyncio.sleep(1)
                    
                except errors.MessageDeleteForbiddenError:
                    print("❌ Нет прав для удаления некоторых сообщений")
                    break
                except errors.FloodWait as e:
                    print(f"⏰ Слишком много запросов. Ждем {e.seconds} секунд...")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"❌ Ошибка при удалении: {e}")
                    break
            
            print(f"✅ Удалено {deleted_count} сообщений в группе {group['name']}")
            
            if show_menu:
                await self.show_main_menu()
            
            return deleted_count
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            if show_menu:
                await self.show_main_menu()
            return 0
    
    async def run(self):
        """Основной цикл работы"""
        await self.start()

async def main():
    """Основная функция"""
    if API_ID == 12345 or API_HASH == "your_api_hash_here":
        print("❌ Пожалуйста, настройте API_ID и API_HASH в файле config.py")
        print("\n📋 Как получить API_ID и API_HASH:")
        print("1. Перейдите на https://my.telegram.org")
        print("2. Войдите с вашим номером телефона")
        print("3. Перейдите в 'API development tools'")
        print("4. Создайте новое приложение")
        print("5. Скопируйте API_ID и API_HASH")
        return
    
    deleter = UserMessageDeleter()
    try:
        await deleter.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Прерывание пользователем")
        print("🧹 Очистка сессионных файлов...")
        await deleter.cleanup_sessions()
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")
        print("🧹 Очистка сессионных файлов...")
        await deleter.cleanup_sessions()

if __name__ == "__main__":
    asyncio.run(main())

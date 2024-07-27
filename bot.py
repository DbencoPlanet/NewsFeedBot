import logging
import requests
import schedule
import time
import os
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client['web3_updates']
subscribers_collection = db['subscribers']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    if subscribers_collection.find_one({"chat_id": chat_id}) is None:
        subscribers_collection.insert_one({"chat_id": chat_id})
        await update.message.reply_text('Hi! You are now subscribed to Web3 updates.')
        logger.info(f"User {chat_id} subscribed for updates.")
    else:
        await update.message.reply_text('You are already subscribed to Web3 updates.')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    if subscribers_collection.find_one({"chat_id": chat_id}):
        subscribers_collection.delete_one({"chat_id": chat_id})
        await update.message.reply_text('You have unsubscribed from Web3 updates.')
        logger.info(f"User {chat_id} unsubscribed from updates.")
    else:
        await update.message.reply_text('You are not subscribed to Web3 updates.')

def fetch_web3_news() -> str:
    response = requests.get(f'https://newsapi.org/v2/everything?q=web3&apiKey={NEWS_API_KEY}', verify=False)
    news_data = response.json()
    articles = news_data.get('articles', [])
    if not articles:
        return "No Web3 news available at the moment."

    top_articles = articles[:3]  # Get the top 3 articles
    news_summary = ""
    for article in top_articles:
        news_summary += (
            f"*{article['title']}*\n"
            f"{article['description']}\n"
            f"[Read more]({article['url']})\n"
            f"![image]({article['urlToImage']})\n\n"
        )
    return news_summary

def fetch_twitter_insights() -> str:
    influencer_ids = [
        '295218901',  # Vitalik Buterin
        '25560012',   # Gavin Wood
        '217801264',  # Balaji Srinivasan
        '1469101279', # Andreas M. Antonopoulos
        '304855551',  # Laura Shin
        '13765392',   # Erik Voorhees
        '121664618',  # Charlie Lee
        '382540493',  # Anthony Pompliano
        '828647717307011072', # Peter McCormack
        '6128602',    # Meltem Demirors
    ]
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    insights = ""
    for user_id in influencer_ids:
        response = requests.get(f'https://api.twitter.com/2/users/{user_id}/tweets', headers=headers, verify=False)
        tweets = response.json()
        if 'data' in tweets and tweets['data']:
            tweet = tweets['data'][0]
            insights += f"[{tweet['text'][:50]}...](https://twitter.com/i/web/status/{tweet['id']})\n\n"
    return insights if insights else "No insights available at the moment."

def fetch_crypto_projects() -> str:
    response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 3,  # Get top 3 projects
        'page': 1,
        'sparkline': False
    }, verify=False)
    projects = response.json()
    if not projects:
        return "No projects available at the moment."
    
    projects_summary = ""
    for project in projects:
        projects_summary += (
            f"[{project['name']} ({project['symbol'].upper()})](https://www.coingecko.com/en/coins/{project['id']}): "
            f"${project['current_price']} - Market Cap: ${project['market_cap']:,}\n\n"
        )
    return projects_summary

async def send_news(bot: Bot) -> None:
    news = fetch_web3_news()
    for subscriber in subscribers_collection.find():
        chat_id = subscriber["chat_id"]
        await bot.send_message(chat_id=chat_id, text=f"Daily Web3 News Roundup:\n{news}", parse_mode=ParseMode.MARKDOWN)
    logger.info("Sent news to all subscribed users.")

async def send_insights(bot: Bot) -> None:
    insights = fetch_twitter_insights()
    for subscriber in subscribers_collection.find():
        chat_id = subscriber["chat_id"]
        await bot.send_message(chat_id=chat_id, text=f"Expert Insights:\n{insights}", parse_mode=ParseMode.MARKDOWN)
    logger.info("Sent insights to all subscribed users.")

async def send_project_spotlight(bot: Bot) -> None:
    projects = fetch_crypto_projects()
    for subscriber in subscribers_collection.find():
        chat_id = subscriber["chat_id"]
        await bot.send_message(chat_id=chat_id, text=f"Top 3 Crypto Projects:\n{projects}", parse_mode=ParseMode.MARKDOWN)
    logger.info("Sent project spotlight to all subscribed users.")

# Test command handlers
async def test_send_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    await send_news(bot)

async def test_send_insights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    await send_insights(bot)

async def test_send_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    await send_project_spotlight(bot)

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("news", test_send_news))
    application.add_handler(CommandHandler("insights", test_send_insights))
    application.add_handler(CommandHandler("project", test_send_project))

    application.run_polling()
    logger.info("Bot started polling...")

    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    schedule.every().day.at("08:00").do(lambda: send_news(bot))
    schedule.every().day.at("12:00").do(lambda: send_insights(bot))
    schedule.every().day.at("16:00").do(lambda: send_project_spotlight(bot))

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()








# import logging
# import requests
# import schedule
# import time
# import os
# from telegram import Update, Bot
# from telegram.constants import ParseMode
# from telegram.ext import Application, CommandHandler, ContextTypes
# from dotenv import load_dotenv
# from pymongo import MongoClient

# # Load environment variables from .env file
# load_dotenv()

# TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# NEWS_API_KEY = os.getenv('NEWS_API_KEY')
# TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
# MONGO_URI = os.getenv('MONGO_URI')

# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# # MongoDB setup
# client = MongoClient(MONGO_URI)
# db = client['web3_updates']
# subscribers_collection = db['subscribers']

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     chat_id = update.message.chat_id
#     if subscribers_collection.find_one({"chat_id": chat_id}) is None:
#         subscribers_collection.insert_one({"chat_id": chat_id})
#         await update.message.reply_text('Hi! You are now subscribed to Web3 updates.')
#         logger.info(f"User {chat_id} subscribed for updates.")
#     else:
#         await update.message.reply_text('You are already subscribed to Web3 updates.')

# async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     chat_id = update.message.chat_id
#     if subscribers_collection.find_one({"chat_id": chat_id}):
#         subscribers_collection.delete_one({"chat_id": chat_id})
#         await update.message.reply_text('You have unsubscribed from Web3 updates.')
#         logger.info(f"User {chat_id} unsubscribed from updates.")
#     else:
#         await update.message.reply_text('You are not subscribed to Web3 updates.')

# def fetch_web3_news() -> str:
#     response = requests.get(f'https://newsapi.org/v2/everything?q=web3&apiKey={NEWS_API_KEY}')
#     news_data = response.json()
#     articles = news_data.get('articles', [])
#     if not articles:
#         return "No Web3 news available at the moment."

#     top_articles = articles[:3]  # Get the top 3 articles
#     news_summary = ""
#     for article in top_articles:
#         news_summary += (
#             f"*{article['title']}*\n"
#             f"{article['description']}\n"
#             f"[Read more]({article['url']})\n"
#             f"![image]({article['urlToImage']})\n\n"
#         )
#     return news_summary

# def fetch_twitter_insights() -> str:
#     influencer_ids = [
#         '295218901',  # Vitalik Buterin
#         '25560012',   # Gavin Wood
#         '217801264',  # Balaji Srinivasan
#         '1469101279', # Andreas M. Antonopoulos
#         '304855551',  # Laura Shin
#         '13765392',   # Erik Voorhees
#         '121664618',  # Charlie Lee
#         '382540493',  # Anthony Pompliano
#         '828647717307011072', # Peter McCormack
#         '6128602',    # Meltem Demirors
#     ]
#     headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
#     insights = ""
#     for user_id in influencer_ids:
#         response = requests.get(f'https://api.twitter.com/2/users/{user_id}/tweets', headers=headers)
#         tweets = response.json()
#         if 'data' in tweets and tweets['data']:
#             tweet = tweets['data'][0]
#             insights += f"[{tweet['text'][:50]}...](https://twitter.com/i/web/status/{tweet['id']})\n\n"
#     return insights if insights else "No insights available at the moment."

# def fetch_crypto_projects() -> str:
#     response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
#         'vs_currency': 'usd',
#         'order': 'market_cap_desc',
#         'per_page': 3,  # Get top 3 projects
#         'page': 1,
#         'sparkline': False
#     })
#     projects = response.json()
#     if not projects:
#         return "No projects available at the moment."
    
#     projects_summary = ""
#     for project in projects:
#         projects_summary += (
#             f"[{project['name']} ({project['symbol'].upper()})](https://www.coingecko.com/en/coins/{project['id']}): "
#             f"${project['current_price']} - Market Cap: ${project['market_cap']:,}\n\n"
#         )
#     return projects_summary

# async def send_news(bot: Bot) -> None:
#     news = fetch_web3_news()
#     for subscriber in subscribers_collection.find():
#         chat_id = subscriber["chat_id"]
#         await bot.send_message(chat_id=chat_id, text=f"Daily Web3 News Roundup:\n{news}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent news to all subscribed users.")

# async def send_insights(bot: Bot) -> None:
#     insights = fetch_twitter_insights()
#     for subscriber in subscribers_collection.find():
#         chat_id = subscriber["chat_id"]
#         await bot.send_message(chat_id=chat_id, text=f"Expert Insights:\n{insights}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent insights to all subscribed users.")

# async def send_project_spotlight(bot: Bot) -> None:
#     projects = fetch_crypto_projects()
#     for subscriber in subscribers_collection.find():
#         chat_id = subscriber["chat_id"]
#         await bot.send_message(chat_id=chat_id, text=f"Top 3 Crypto Projects:\n{projects}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent project spotlight to all subscribed users.")

# # Test command handlers
# async def test_send_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_news(bot)

# async def test_send_insights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_insights(bot)

# async def test_send_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_project_spotlight(bot)

# def main() -> None:
#     application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("stop", stop))
#     application.add_handler(CommandHandler("news", test_send_news))
#     application.add_handler(CommandHandler("insights", test_send_insights))
#     application.add_handler(CommandHandler("project", test_send_project))

#     application.run_polling()
#     logger.info("Bot started polling...")

#     bot = Bot(token=TELEGRAM_BOT_TOKEN)

#     schedule.every().day.at("08:00").do(lambda: send_news(bot))
#     schedule.every().day.at("12:00").do(lambda: send_insights(bot))
#     schedule.every().day.at("16:00").do(lambda: send_project_spotlight(bot))

#     while True:
#         schedule.run_pending()
#         time.sleep(1)

# if __name__ == '__main__':
#     main()






# import logging
# import requests
# import schedule
# import time
# import os
# from telegram import Update, Bot
# from telegram.constants import ParseMode
# from telegram.ext import Application, CommandHandler, ContextTypes
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# NEWS_API_KEY = os.getenv('NEWS_API_KEY')
# TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# subscribed_users = set()

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     chat_id = update.message.chat_id
#     if chat_id not in subscribed_users:
#         subscribed_users.add(chat_id)
#         await update.message.reply_text('Hi! You are now subscribed to Web3 updates.')
#         logger.info(f"User {chat_id} subscribed for updates.")
#     else:
#         await update.message.reply_text('You are already subscribed to Web3 updates.')

# async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     chat_id = update.message.chat_id
#     if chat_id in subscribed_users:
#         subscribed_users.remove(chat_id)
#         await update.message.reply_text('You have unsubscribed from Web3 updates.')
#         logger.info(f"User {chat_id} unsubscribed from updates.")
#     else:
#         await update.message.reply_text('You are not subscribed to Web3 updates.')

# def fetch_web3_news() -> str:
#     response = requests.get(f'https://newsapi.org/v2/everything?q=web3&apiKey={NEWS_API_KEY}')
#     news_data = response.json()
#     articles = news_data.get('articles', [])
#     if not articles:
#         return "No Web3 news available at the moment."

#     top_articles = articles[:3]  # Get the top 3 articles
#     news_summary = ""
#     for article in top_articles:
#         news_summary += (
#             f"*{article['title']}*\n"
#             f"{article['description']}\n"
#             f"[Read more]({article['url']})\n"
#             f"![image]({article['urlToImage']})\n\n"
#         )
#     return news_summary

# def fetch_twitter_insights() -> str:
#     influencer_ids = [
#         '295218901',  # Vitalik Buterin
#         '25560012',   # Gavin Wood
#         '217801264',  # Balaji Srinivasan
#         '1469101279', # Andreas M. Antonopoulos
#         '304855551',  # Laura Shin
#         '13765392',   # Erik Voorhees
#         '121664618',  # Charlie Lee
#         '382540493',  # Anthony Pompliano
#         '828647717307011072', # Peter McCormack
#         '6128602',    # Meltem Demirors
#     ]
#     headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
#     insights = ""
#     for user_id in influencer_ids:
#         response = requests.get(f'https://api.twitter.com/2/users/{user_id}/tweets', headers=headers)
#         tweets = response.json()
#         if 'data' in tweets and tweets['data']:
#             tweet = tweets['data'][0]
#             insights += f"[{tweet['text'][:50]}...](https://twitter.com/i/web/status/{tweet['id']})\n\n"
#     return insights if insights else "No insights available at the moment."

# def fetch_crypto_projects() -> str:
#     response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
#         'vs_currency': 'usd',
#         'order': 'market_cap_desc',
#         'per_page': 3,  # Get top 3 projects
#         'page': 1,
#         'sparkline': False
#     })
#     projects = response.json()
#     if not projects:
#         return "No projects available at the moment."
    
#     projects_summary = ""
#     for project in projects:
#         projects_summary += (
#             f"[{project['name']} ({project['symbol'].upper()})](https://www.coingecko.com/en/coins/{project['id']}): "
#             f"${project['current_price']} - Market Cap: ${project['market_cap']:,}\n\n"
#         )
#     return projects_summary

# async def send_news(bot: Bot) -> None:
#     news = fetch_web3_news()
#     for chat_id in subscribed_users:
#         await bot.send_message(chat_id=chat_id, text=f"Daily Web3 News Roundup:\n{news}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent news to all subscribed users.")

# async def send_insights(bot: Bot) -> None:
#     insights = fetch_twitter_insights()
#     for chat_id in subscribed_users:
#         await bot.send_message(chat_id=chat_id, text=f"Expert Insights:\n{insights}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent insights to all subscribed users.")

# async def send_project_spotlight(bot: Bot) -> None:
#     projects = fetch_crypto_projects()
#     for chat_id in subscribed_users:
#         await bot.send_message(chat_id=chat_id, text=f"Top 3 Crypto Projects:\n{projects}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent project spotlight to all subscribed users.")

# # Test command handlers
# async def test_send_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_news(bot)

# async def test_send_insights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_insights(bot)

# async def test_send_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_project_spotlight(bot)

# def main() -> None:
#     application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("stop", stop))
#     application.add_handler(CommandHandler("news", test_send_news))
#     application.add_handler(CommandHandler("insights", test_send_insights))
#     application.add_handler(CommandHandler("project", test_send_project))

#     application.run_polling()
#     logger.info("Bot started polling...")

#     bot = Bot(token=TELEGRAM_BOT_TOKEN)

#     schedule.every().day.at("08:00").do(lambda: send_news(bot))
#     schedule.every().day.at("12:00").do(lambda: send_insights(bot))
#     schedule.every().day.at("16:00").do(lambda: send_project_spotlight(bot))

#     while True:
#         schedule.run_pending()
#         time.sleep(1)

# if __name__ == '__main__':
#     main()




# import logging
# import requests
# import schedule
# import time
# import os
# from telegram import Update, Bot
# from telegram.constants import ParseMode
# from telegram.ext import Application, CommandHandler, ContextTypes
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# NEWS_API_KEY = os.getenv('NEWS_API_KEY')
# TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

# logging.basicConfig(
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     level=logging.INFO
# )
# logger = logging.getLogger(__name__)

# subscribed_users = set()

# async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     chat_id = update.message.chat_id
#     if chat_id not in subscribed_users:
#         subscribed_users.add(chat_id)
#         await update.message.reply_text('Hi! You are now subscribed to Web3 updates.')
#         logger.info(f"User {chat_id} subscribed for updates.")
#     else:
#         await update.message.reply_text('You are already subscribed to Web3 updates.')

# async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     chat_id = update.message.chat_id
#     if chat_id in subscribed_users:
#         subscribed_users.remove(chat_id)
#         await update.message.reply_text('You have unsubscribed from Web3 updates.')
#         logger.info(f"User {chat_id} unsubscribed from updates.")
#     else:
#         await update.message.reply_text('You are not subscribed to Web3 updates.')

# def fetch_web3_news() -> str:
#     response = requests.get(f'https://newsapi.org/v2/everything?q=web3&apiKey={NEWS_API_KEY}')
#     news_data = response.json()
#     articles = news_data.get('articles', [])
#     if not articles:
#         return "No Web3 news available at the moment."

#     top_articles = articles[:3]  # Get the top 3 articles
#     news_summary = ""
#     for article in top_articles:
#         news_summary += (
#             f"*{article['title']}*\n"
#             f"{article['description']}\n"
#             f"[Read more]({article['url']})\n"
#             f"![image]({article['urlToImage']})\n\n"
#         )
#     return news_summary

# def fetch_twitter_insights() -> str:
#     influencer_ids = [
#         '295218901',  # Vitalik Buterin
#         '25560012',   # Gavin Wood
#         '217801264',  # Balaji Srinivasan
#         '1469101279', # Andreas M. Antonopoulos
#         '304855551',  # Laura Shin
#         '13765392',   # Erik Voorhees
#         '121664618',  # Charlie Lee
#         '382540493',  # Anthony Pompliano
#         '828647717307011072', # Peter McCormack
#         '6128602',    # Meltem Demirors
#     ]
#     headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
#     insights = ""
#     for user_id in influencer_ids:
#         response = requests.get(f'https://api.twitter.com/2/users/{user_id}/tweets', headers=headers)
#         tweets = response.json()
#         if 'data' in tweets and tweets['data']:
#             tweet = tweets['data'][0]
#             insights += f"[{tweet['text'][:50]}...](https://twitter.com/i/web/status/{tweet['id']})\n\n"
#     return insights if insights else "No insights available at the moment."

# def fetch_crypto_project() -> str:
#     response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
#         'vs_currency': 'usd',
#         'order': 'market_cap_desc',
#         'per_page': 1,
#         'page': 1,
#         'sparkline': False
#     })
#     projects = response.json()
#     if not projects:
#         return "No projects available at the moment."
#     project = projects[0]
#     return f"[{project['name']} ({project['symbol'].upper()})](https://www.coingecko.com/en/coins/{project['id']}): ${project['current_price']} - Market Cap: ${project['market_cap']:,}"

# async def send_news(bot: Bot) -> None:
#     news = fetch_web3_news()
#     for chat_id in subscribed_users:
#         await bot.send_message(chat_id=chat_id, text=f"Daily Web3 News Roundup:\n{news}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent news to all subscribed users.")

# async def send_insights(bot: Bot) -> None:
#     insights = fetch_twitter_insights()
#     for chat_id in subscribed_users:
#         await bot.send_message(chat_id=chat_id, text=f"Expert Insights:\n{insights}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent insights to all subscribed users.")

# async def send_project_spotlight(bot: Bot) -> None:
#     project = fetch_crypto_project()
#     for chat_id in subscribed_users:
#         await bot.send_message(chat_id=chat_id, text=f"Project Spotlight:\n{project}", parse_mode=ParseMode.MARKDOWN)
#     logger.info("Sent project spotlight to all subscribed users.")

# # Test command handlers
# async def test_send_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_news(bot)

# async def test_send_insights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_insights(bot)

# async def test_send_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
#     bot = context.bot
#     await send_project_spotlight(bot)

# def main() -> None:
#     application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("stop", stop))
#     application.add_handler(CommandHandler("news", test_send_news))
#     application.add_handler(CommandHandler("insights", test_send_insights))
#     application.add_handler(CommandHandler("project", test_send_project))

#     application.run_polling()
#     logger.info("Bot started polling...")

#     bot = Bot(token=TELEGRAM_BOT_TOKEN)

#     schedule.every().day.at("08:00").do(lambda: send_news(bot))
#     schedule.every().day.at("12:00").do(lambda: send_insights(bot))
#     schedule.every().day.at("16:00").do(lambda: send_project_spotlight(bot))

#     while True:
#         schedule.run_pending()
#         time.sleep(1)

# if __name__ == '__main__':
#     main()



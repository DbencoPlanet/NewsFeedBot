import logging
import requests
import schedule
import time
import os
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

subscribed_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued and subscribe the user."""
    chat_id = update.message.chat_id
    subscribed_users.add(chat_id)
    await update.message.reply_text('Hi! You are now subscribed to Web3 updates.')
    logger.info(f"User {chat_id} subscribed for updates.")

def fetch_web3_news() -> str:
    """Fetch Web3 news from NewsAPI."""
    response = requests.get(f'https://newsapi.org/v2/everything?q=web3&apiKey={NEWS_API_KEY}')
    news_data = response.json()
    articles = news_data.get('articles', [])
    if not articles:
        return "No Web3 news available at the moment."
    top_article = articles[0]
    return f"{top_article['title']} - {top_article['source']['name']}\n{top_article['url']}"

def fetch_twitter_insights() -> str:
    """Fetch latest tweets from Web3 influencers using Twitter API."""
    influencer_ids = [
        '295218901',  # Vitalik Buterin
        '25560012',   # Gavin Wood
        '217801264',  # Balaji Srinivasan
    ]
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    insights = ""
    for user_id in influencer_ids:
        response = requests.get(f'https://api.twitter.com/2/users/{user_id}/tweets', headers=headers)
        tweets = response.json()
        if 'data' in tweets and tweets['data']:
            tweet = tweets['data'][0]
            insights += f"{tweet['text']}\nhttps://twitter.com/i/web/status/{tweet['id']}\n\n"
    return insights if insights else "No insights available at the moment."

def fetch_crypto_project() -> str:
    """Fetch a cryptocurrency project from CoinGecko API."""
    response = requests.get('https://api.coingecko.com/api/v3/coins/markets', params={
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 1,
        'page': 1,
        'sparkline': False
    })
    projects = response.json()
    if not projects:
        return "No projects available at the moment."
    project = projects[0]
    return f"{project['name']} ({project['symbol'].upper()}): ${project['current_price']} - Market Cap: ${project['market_cap']:,}\n![Image]({project['image']})"

async def send_news(bot: Bot) -> None:
    """Send news to all subscribed users."""
    news = fetch_web3_news()
    for chat_id in subscribed_users:
        await bot.send_message(chat_id=chat_id, text=f"Daily Web3 News Roundup:\n{news}", parse_mode=ParseMode.MARKDOWN)
    logger.info("Sent news to all subscribed users.")

async def send_insights(bot: Bot) -> None:
    """Send expert insights to all subscribed users."""
    insights = fetch_twitter_insights()
    for chat_id in subscribed_users:
        await bot.send_message(chat_id=chat_id, text=f"Expert Insights:\n{insights}", parse_mode=ParseMode.MARKDOWN)
    logger.info("Sent insights to all subscribed users.")

async def send_project_spotlight(bot: Bot) -> None:
    """Send project spotlight to all subscribed users."""
    project = fetch_crypto_project()
    for chat_id in subscribed_users:
        await bot.send_message(chat_id=chat_id, text=f"Project Spotlight:\n{project}", parse_mode=ParseMode.MARKDOWN)
    logger.info("Sent project spotlight to all subscribed users.")

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))

    # Start the Bot
    application.run_polling()
    logger.info("Bot started polling...")

    # Schedule tasks
    bot = Bot(TELEGRAM_BOT_TOKEN)

    schedule.every().day.at("08:00").do(lambda: send_news(bot))
    schedule.every().day.at("12:00").do(lambda: send_insights(bot))
    schedule.every().day.at("16:00").do(lambda: send_project_spotlight(bot))

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()

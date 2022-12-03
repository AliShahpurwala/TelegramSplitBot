from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler
from models import User, Session, engine, Receipt, Tag
from telegram import Update
import bot
import split

async def set_new_currency(update, context):
    # First find the user who requested this
    request_user_id = update.message['from']['id']
    user_first_name_string = update.message['from']['first_name']
    
    bot.check_if_user_exists(request_user_id, user_first_name_string)
    
    # Find the user object
    user_obj = bot.SESSION.query(User).filter(User.user_id == request_user_id).first()
    user_preferred_currency_string = split.find_preferred_currency(request_user_id)

    chat_id = update.message.chat.id
    full_caption = update.message.text
    # Filter out all non cashtag entities
    message_entities = update.message.entities
    filtered_message_entities = list(filter(lambda x : x['type'] == 'cashtag', message_entities))
    # The user is only allowed to specify one currency
    if len(filtered_message_entities) == 0:
        await context.bot.send_message(chat_id, f'No currency found in message. User currency\
        currently set at {user_preferred_currency_string}')
        return
    currency_cashtag_entity = filtered_message_entities[0]
    currency_string_start = currency_cashtag_entity['offset'] + 1
    currency_string_end = currency_string_start + currency_cashtag_entity['length']
    currency_short_form = full_caption[currency_string_start : currency_string_end].strip()
    if len(filtered_message_entities) == 1:
        await context.bot.send_message(chat_id, f'Will set {currency_short_form} as your\
        prferred language.')
    else:
        await context.bot.send_message(chat_id, f'Found multiple currency tags. Changing\
        your preferred currency to the first one found \
        which is {currency_short_form}')
    user_obj.preferred_currency = currency_short_form
    bot.SESSION.commit()

async def help_menu_command(update, context):
    request_user = update.message['from']
    final_return_string = ''
    if (bot.SESSION.query(User).filter(User.user_id == request_user.id).first() is None):
        final_return_string += f'Hiya {request_user.first_name}! Receipt Bot here\n'
        final_return_string += 'We\'ve gone ahead and set up an account for you already\n'
        final_return_string += f'Your unique identifier is {request_user.id} (I know it looks scary but don\'t worry you don\'t need to remember it haha)\n'
        final_return_string += 'Here\'s just a couple cool things I can do :)'
    else:
        final_return_string += f'Welcome back {request_user.first_name}. We\'ve missed you :)\n'
        final_return_string += f'Here\'s some quick reminders on how I can help\n'
    final_return_string += '\n\n'
    final_return_string += '**Receipt Commands**\n'
    final_return_string += '1) Want to save a receipt ?\n'
    final_return_string += 'Just attach an image of the receipt and put the following in the caption\n'
    final_return_string += '/receipt #tag\n'
    final_return_string += 'We\'ll take care of the rest from there! You can add any number of hashtags which will be handy to find these receipts later on!'
    final_return_string += '\n2) Want to find a saved receipt ?\n'
    final_return_string += 'We have 2 commands you could use here\n'
    final_return_string += 'Use either /findbydate followed by the date in either dd/mm/yyyy or dd-mm-yyyy\n'
    final_return_string += 'You can also use /findbytags followed by #tag with any number of tags! However, we will only return receipts that have all said tags so be careful!\n'
    final_return_string += '\nThat\'s all we have for now! Keep checking back for new and cool features :)' 
    await context.bot.send_message(update.message.chat.id, final_return_string)
from telegram import Update 
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler
from models import User, Session, engine, Receipt, Tag, Transaction, Account
import bot


async def split_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    request_user_id = update.message['from']['id']
    request_user = bot.SESSION.query(User).filter(User.user_id == request_user_id).first()
    
    chat_id = update.message.chat.id
    full_caption_string = update.message.caption
    all_caption_entities = update.message.caption_entities

    currency_string = await find_currency(update, context)

    # this is only if it is an image
    if (len(update.message.photo) != 0):
        photo_sizes_list = update.message.photo
        photo_date_timestamp = update.message.date
        photo_sent = photo_sizes_list[len(photo_sizes_list) - 1]
        photo_sent_id = photo_sent['file_id']            
            
    # Lets find all the hashtags in the given caption
    all_hashtags = list(filter(lambda x : x['type'] == 'hashtag', all_caption_entities))

    # Return all hastags as a list
    string_list_of_hashtags = bot.find_all_hashtags_from_entities(
        full_caption_string,
        all_hashtags
        )

    receipt_obj = Receipt(receipt_id = photo_sent_id, by_user = request_user_id, 
    date = photo_date_timestamp)

    # Loop through all tags
    for tag in string_list_of_hashtags:
        # If tag doesnt exist, create it
        if not bot.check_if_tag_exists(tag):
            tag_obj = bot.create_tag(tag)
        else:
            tag_obj = bot.SESSION.query(Tag).filter(Tag.tag_name == tag).first()

        # Now the tag exists for sure
        # Add the tag to the receipt
        receipt_obj.tags.append(tag_obj)
            
    bot.SESSION.add(receipt_obj)
    bot.SESSION.commit()

    split_among_users = await find_users_to_split(update, context)
    current_transaction_id = await create_transaction(update, context, receipt_obj)
    await create_split_accounts(current_transaction_id, split_among_users, update, context)

async def create_transaction(update, context, receipt_obj):
    """
    Args:
    update : Update
    context : ContextTypes.DEFAULT_TYPE
    receipt_obj : Receipt
    Returns:
    transaction_id : Int
    """
    request_chat_id = update.message.chat.id
    new_transaction_obj = Transaction()
    num_transactions = len(bot.SESSION.query(Transaction).all())
    new_transaction_obj.transaction_id = num_transactions + 1
    new_transaction_obj.receipt_id = receipt_obj.receipt_id
    new_transaction_obj.paid_by = receipt_obj.by_user
    bot.SESSION.add(new_transaction_obj)
    bot.SESSION.commit()
    await context.bot.send_message(request_chat_id, f'New transaction created with ID number {new_transaction_obj.transaction_id}')
    return new_transaction_obj.transaction_id

async def create_split_accounts(current_transaction_id, split_among_users, update, context):

    request_chat_id = update.message.chat.id
    request_user_id = update.message['from']['id']
    request_user_first_name = update.message['from']['first_name']

    if len(split_among_users) < 1:
        await context.bot.send_message(request_chat_id, 'No users found to split amongst')
        return
    
    # First check that all user accounts exist
    for user in split_among_users:
        bot.check_if_user_exists(user.user_id, user.first_name)
    
    # Create all the account objects
    # We assume that all the amounts follow the user
    full_caption = update.message.caption
    full_caption_list = full_caption.split(' ')

    current_transaction = bot.SESSION.query(Transaction).filter(
        Transaction.transaction_id == current_transaction_id
    ).first()

    for user in split_among_users:
        index_of_user_mention = full_caption_list.index(user.first_name)
        try:
            amount = full_caption_list[index_of_user_mention + 1]
        except ValueError:
            await context.bot.send_message(request_chat_id, f'Couldn\'t find an amount for {user.first_name}.')
            continue
        except IndexError:
            await context.bot.send_message(request_chat_id, f'Did you forget an amount for {user.first_name}?')
            return
        else:
            new_account = Account()
            new_account.transaction_id = current_transaction_id
            new_account.from_user = request_user_id
            new_account.to_user = user.user_id
            new_account.amount = amount
            await context.bot.send_message(request_chat_id, f'{request_user_first_name} has paid \
            {amount} for {user.first_name}')
            current_transaction.accounts.append(new_account)
            bot.SESSION.add(new_account)
            bot.SESSION.commit()

async def find_users_to_split(update, context):
    """
    Args:
        update : Update
        context : ContextTypes.DEFAULT_TYPE
    Return:
        [User]
    """
    request_chat_id = update.message.chat.id
    
    all_caption_entities = update.message.caption_entities
    mention_entities = list(filter(lambda x : x['type'] == 'text_mention', all_caption_entities))
    
    # Create a list of the user objects
    split_among_users = []
    for mention in mention_entities:
        bot.check_if_user_exists(mention.user.id, mention.user.first_name)
        split_user = bot.SESSION.query(User).filter(User.user_id == mention.user.id).first()
        split_among_users.append(split_user)
    
    return split_among_users

async def find_currency(update, context):
    """
    Args
    update : Update
    context : ContextTypes.DEFAULT_TYPE
    Return
    String

    Desc
    We accept the list of message entities. Filter out the non cashtag entities. Return
    if there is only one currency sent with the short form of the currency.
    """
    request_user_id = update.message['from']['id']
    chat_id = update.message.chat.id
    full_caption = update.message.caption
    # Filter out all non cashtag entities
    message_entities = update.message.caption_entities
    filtered_message_entities = list(filter(lambda x : x['type'] == 'cashtag', message_entities))
    # The user is only allowed to specify one currency
    if len(filtered_message_entities) == 0:
        user_preferred_currency_string = find_preferred_currency(request_user_id)
        await context.bot.send_message(chat_id, f'No currency found in message. Using user set default\
        which is {user_preferred_currency_string}')
        return user_preferred_currency_string
    currency_cashtag_entity = filtered_message_entities[0]
    currency_string_start = currency_cashtag_entity['offset'] + 1
    currency_string_end = currency_string_start + currency_cashtag_entity['length']
    currency_short_form = full_caption[currency_string_start : currency_string_end].strip()
    if len(filtered_message_entities) == 1:
        await context.bot.send_message(chat_id, f'Will use {currency_short_form} as requested.')
    else:
        await context.bot.send_message(chat_id, f'Found multiple currency tags. Resorting to the first one found \
        which is {currency_short_form}')  
    return currency_short_form

def find_preferred_currency(request_user_id):
    """
    Args
    request_user_id : Integer
    
    Return
    String
    """
    request_user = bot.SESSION.query(User).filter(User.user_id == request_user_id).first()
    return request_user.preferred_currency

import helper_commands
from telegram import Update 
from split import *
from PIL import Image
import pytesseract
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, filters, MessageHandler
from models import User, Session, engine, Receipt, Tag
import time
import threading
import pathlib
from datetime import datetime

TOKEN = '5539063247:AAHuuxlcXqixTJoqoqDtvBDyrjnGza0VcB0'
SESSION = Session(bind = engine)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(update.message)
    await context.bot.send_message(chat_id = update.effective_chat.id, text = "Hello World!")

async def receipt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Got your receipt!")


async def attachment_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    entities = update.message.caption_entities
    all_bot_commands = list(filter(lambda x : x['type'] == 'bot_command' , entities))
    attachment_caption = update.message.caption
    for current_bot_command in all_bot_commands:
        offset_start = current_bot_command['offset'] + 1
        string_end = offset_start + current_bot_command['length']
        # Remember to always strip the content from text / captions
        if (attachment_caption[offset_start : string_end].lower().strip() == 'receipt'):
            from_user_id = update.message['from']['id']
            user_found_bool = False if len(SESSION.query(User).filter(User.user_id == from_user_id).all()) == 0 else True
            if not user_found_bool:
                new_user = User(user_id = from_user_id, first_name = update.message['from']['first_name'])
                SESSION.add(new_user)
                SESSION.commit()
            user_found = SESSION.query(User).filter(User.user_id == from_user_id).first()

            
            # what if it is a file
            # then consider that
            
            # this is only if it is an image
            if (len(update.message.photo) != 0):
                photo_sizes_list = update.message.photo
                photo_date_timestamp = update.message.date
                photo_sent = photo_sizes_list[len(photo_sizes_list) - 1]
                photo_sent_id = photo_sent['file_id']            
            
            # Lets find all the hashtags in the given caption
            all_hashtags = list(filter(lambda x : x['type'] == 'hashtag', entities))

            # Return all hastags as a list
            string_list_of_hashtags = find_all_hashtags_from_entities(
                attachment_caption,
                all_hashtags
            )

            receipt_obj = Receipt(receipt_id = photo_sent_id, by_user = from_user_id, 
            date = photo_date_timestamp)

            # Loop through all tags
            for tag in string_list_of_hashtags:

                # If tag doesnt exist, create it
                if not check_if_tag_exists(tag):

                    tag_obj = create_tag(tag)
                else:
                    tag_obj = SESSION.query(Tag).filter(Tag.tag_name == tag).first()
                # Now the tag exists for sure
                # Add the tag to the receipt
                receipt_obj.tags.append(tag_obj)
            

            SESSION.add(receipt_obj)
            SESSION.commit()
        elif(attachment_caption[offset_start : string_end].lower().strip() == 'split'):
            from_user_id = update.message['from']['id']
            user_found_bool = False if len(SESSION.query(User).filter(User.user_id == from_user_id).all()) == 0 else True
            if not user_found_bool:
                new_user = User(user_id = from_user_id, first_name = update.message['from']['first_name'])
                SESSION.add(new_user)
                SESSION.commit()
            await split_command(update, context)



def create_tag(tag_string):
    new_tag = Tag(tag_name = tag_string)
    SESSION.add(new_tag)
    SESSION.commit()
    return new_tag

def check_if_tag_exists(tag_string):

    found_tag = SESSION.query(Tag).filter(Tag.tag_name == tag_string).all()
    if found_tag == []:
        return False
    return True

def find_all_hashtags_from_entities(full_attachment_caption, hashtag_entities):
        """
        Returns a list of strings with all the tags
        """
        all_hashtags_string_list = []
        for hashtag in hashtag_entities:
            offset_start = hashtag['offset'] + 1
            string_end = offset_start + hashtag['length']
            all_hashtags_string_list.append(
                full_attachment_caption[offset_start: string_end].strip()
            )
        return all_hashtags_string_list


    # if 'receipt' in caption_sent and caption_sent is not None:
    #     await update.message.reply_text('Got your receipt!')
        
    #     photo_sizes_list = update.message.photo
        
    #     photo_sent = photo_sizes_list[
    #         len(photo_sizes_list) - 1
    #         ]
        
    #     photo_sent_id = photo_sent.file_id
    #     send_out = None
        
    #     file_object = await photo_sent.get_file()
        
    #     file_download = await file_object.download(
    #         custom_path = pathlib.Path(f'./saved_receipts/{photo_sent_id}.jpg')
    #     )
        
    #     pic_string = pytesseract.image_to_string(Image.open(file_download))
        
    # else:
    #     await update.message.reply_text('Did you mean to send a receipt ?')
    

async def thread_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    thread = threading.Thread(target = test_thread, args = (1, ))
    await update.message.reply_text('Start thread, will sleep for 10 seconds')
    thread.start()

def test_thread(name):
    time.sleep(10)    

async def find_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):


    # First retrieve the user id
    request_user_id = update.message['from']['id']

    # Check if this user exists
    find_user = SESSION.query(User).filter(User.user_id == request_user_id)

    if find_user is None:
        # User does not exist in the system
        # Create this user for future use
        request_user_first_name = udpate.message['from']['first_name']
        new_user = User(user_id = request_user_id, first_name = request_user_first_name)
        SESSION.add(new_user)
        SESSION.commit()
        await udpate.message.reply_text('You have no previous records in the system')
    else:
    
        # Now the user exists in the system
        # Now find all their records
        request_user_receipts = list(SESSION.query(Receipt).filter(Receipt.by_user == request_user_id))
        num_records = len(request_user_receipts)

        await update.message.reply_text(f'Found {num_records} records')

        # For now just send all the receipt ids back to the user on telegram
        # Lets now send thea actual files instead
        request_chat_id = update.message['chat']['id']

        for receipt in request_user_receipts:
            
            await context.bot.send_photo(
                request_chat_id, 
                receipt.receipt_id, 
                caption = receipt.date.strftime('%A %B %d, %Y'),
                disable_notification = True)

async def test_command(update, context):
    all_entities = update.message.entities
    all_hashtags = list(filter(lambda x : x['type'] == 'hashtag', all_entities))
    await update.message.reply_text(find_all_hashtags_from_entities(
        update.message.text,
        all_hashtags
    ))

async def find_by_tags(update, context):

    request_chat_id = update.message.chat.id
    request_user_id = update.message['from']['id']

    # Find the list of hashtags given
    all_tags = find_all_hashtags_from_entities(
        update.message.text,
        list(filter(lambda x : x['type'] == 'hashtag', update.message.entities))
    )

    all_receipts = SESSION.query(Receipt).filter(User.user_id == request_user_id).all()

    receipt_with_given_tags = []

    for receipt in all_receipts:
        print(receipt)
        tag_not_found = False

        for tag in all_tags:

            if tag not in list(map(lambda x : x.tag_name, receipt.tags)):
                tag_not_found = True

        if not tag_not_found:
            receipt_with_given_tags.append(receipt)

    num_records = len(receipt_with_given_tags)

    await update.message.reply_text(f'Found {num_records} record(s) with the tags {all_tags}')

    for receipt in receipt_with_given_tags:

        await context.bot.send_photo(
            request_chat_id,
            receipt.receipt_id
        )

async def find_by_date(update, context):

    # Find all receeipts by the current user by date
    request_user_id = update.message['from']['id']
    request_user_first_name = update.message['from']['first_name']
    
    if not check_if_user_exists(request_user_id, request_user_first_name):
        await update.message.reply_text('No records found')

    else:
        # The user already existed, checking their records now
        # First lets parse the given date
        # Assuming the format is dd/mm/yyyy

        # Assuming that the date is the second argument
        try:
            given_date_string = update.message.text.split(' ')[1]
        except IndexError:
            await update.message.reply_text('Date not provided')
            return 

        # Time to parse the string into a date
        try:
            given_date = datetime.strptime(given_date_string, "%d/%m/%Y")
        except ValueError:

            # Try parsing another format
            try:
                given_date = datetime.strptime(given_date_string, "%d-%m-%Y")
            except ValueError:
                await update.message.reply_text('Could not parse your date')
                return
        
        # If we reach here, we successfully parsed the date
        # Subtract the two timestamps and if it is less than 24 hours in seconds then were good
        # Will have to manually filter
        records_by_user = list(
            SESSION.query(Receipt).filter(Receipt.by_user == request_user_id)
            )

        records_on_date = []

        for record in records_by_user:
            if (record.date - given_date).days == 0:
                records_on_date.append(record)

        request_chat_id = update.message['chat']['id']

        num_records = len(records_on_date)
        
        await update.message.reply_text(f'Found {num_records} record(s) on {given_date_string}')

        # Send back the results
        for record in records_on_date:

            await context.bot.send_photo(
                request_chat_id,
                record.receipt_id
            )

def check_if_user_exists(user_id, first_name):
    """
    Check if the user exists if not create a new user in the database
    """
    # Helper function to find if a user exists
    find_user = SESSION.query(User).filter(User.user_id == user_id).first()
    if find_user is None:
        new_user = User(user_id = user_id, first_name = first_name)
        SESSION.add(new_user)
        SESSION.commit()
        return False
    else:
        return True

async def end_command(update, context):
    first_name = update.message['from']['first_name']
    await update.message.reply_text(f'{first_name} is a cool guy')

async def all_message_handler(update, context):
    print(update.message)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('receipt', receipt_command))
    app.add_handler(CommandHandler('thread', thread_command))
    app.add_handler(CommandHandler('test', test_command))
    app.add_handler(CommandHandler('end', end_command))
    app.add_handler(
        CommandHandler(
            'setcurrency',
            helper_commands.set_new_currency
        
        )
    )
    app.add_handler(CommandHandler('help', helper_commands.help_menu_command))
    app.add_handler(
        CommandHandler(
            'findall',
            find_all_command
        )
    )
    app.add_handler(
        CommandHandler(
            'findbydate',
            find_by_date
        )
    )

    app.add_handler(
        CommandHandler(
            'findbytags',
            find_by_tags
        )
    )

    app.add_handler(
        MessageHandler(
            filters.ATTACHMENT,
            attachment_message_handler
        )
    )

    app.add_handler(
        (MessageHandler(
            filters.ALL,
            all_message_handler
        ))
    )


    app.run_polling()

# Database Schema
# Receipt
# user : ForeignKey
# id : str
# 
from sqlalchemy.orm import declarative_base,sessionmaker, relationship 
from sqlalchemy import Column,String,DateTime,Integer,create_engine, ForeignKey, Table, Float
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

connection_string = "sqlite:///"+os.path.join(BASE_DIR,'site.db')

Session = sessionmaker()

Base = declarative_base()

engine = create_engine(connection_string,echo=True)

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer(), primary_key = True) # will be the same as their id on telegram
    first_name = Column(String(), nullable = False) # again will be pulled from telegram
    date_joined = Column(DateTime(), default = datetime.utcnow)
    preferred_currency = Column(String(3), default = 'AED', nullable = False)
    def __init__(self, user_id, first_name):
        self.user_id = user_id
        self.first_name = first_name

    def __repr__(self):
        return f'User with id = {self.user_id}, name = {self.first_name} and joined at {self.date_joined}\
        using the currency {self.preferred_currency}' 

class Receipt(Base):
    __tablename__ = 'receipts'
    receipt_id = Column(String(), primary_key = True) # Using the unique file id
    by_user = Column(Integer(), ForeignKey(User.user_id), nullable = False)
    date = Column(DateTime(), nullable = False)
    tags = relationship('Tag', secondary = 'ReceiptTags', back_populates = 'receipts')

    def __repr__(self):
        return f'Receipt with id = {self.receipt_id} by user with id = {self.by_user} and has tags = {self.tags}'

class Tag(Base):
    __tablename__ = 'tags'
    tag_id = Column(Integer(), primary_key = True)
    tag_name = Column(String(), nullable = False, unique = True) # Will store all as lower case for simplicity
    receipts = relationship('Receipt', secondary = 'ReceiptTags', back_populates = 'tags')

    def __repr__(self):
        return f'Tag with name = {self.tag_name}'

class Transaction(Base):
    __tablename__ = 'Transaction'
    transaction_id = Column(Integer(), primary_key = True)
    receipt_id = Column(String(), ForeignKey(Receipt.receipt_id), nullable = False)
    paid_by = Column(Integer(), ForeignKey(User.user_id), nullable = False)
    accounts = relationship(lambda : Account)

    def __repr__(self):
        return f'Transaction No. {self.transaction_id} with Receipt ID = {self.receipt_id} was paid by User No. {self.paid_by}'

class Account(Base):
    __tablename__ = 'Account'
    transaction_id = Column(Integer(), ForeignKey(Transaction.transaction_id), primary_key = True)
    from_user = Column(Integer(), ForeignKey(User.user_id), primary_key = True)
    to_user = Column(Integer(), ForeignKey(User.user_id), primary_key = True)
    amount = Column(Float(), nullable = False)

    def __repr__(self):
        return f'An account belonging to transaction ID {self.transaction_id} from user with ID {self.from_user} to user\
         with ID {self.to_user} for the amount of {self.amount}'

ReceiptTags = Table(
    'ReceiptTags', Base.metadata,
    Column('receipt_id', ForeignKey('receipts.receipt_id'), primary_key = True),
    Column('tag_id', ForeignKey('tags.tag_id'), primary_key = True)
)
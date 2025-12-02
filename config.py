import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hardnet_secret_key'
    DATABASE = os.environ.get('DATABASE') or 'hardnet.db'

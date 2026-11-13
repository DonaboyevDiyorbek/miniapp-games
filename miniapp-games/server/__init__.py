try:  # .env faylini avtomatik o'qish
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

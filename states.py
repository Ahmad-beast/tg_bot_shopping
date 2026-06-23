from aiogram.fsm.state import State, StatesGroup


class AddProduct(StatesGroup):
    emoji = State()
    name = State()
    price = State()
    desc = State()
    stock = State()


class EditProduct(StatesGroup):
    value = State()


class AddStock(StatesGroup):
    items = State()


class Broadcast(StatesGroup):
    message = State()


class AddBalance(StatesGroup):
    user_id = State()
    amount = State()


class BanUser(StatesGroup):
    user_id = State()


class TopUp(StatesGroup):
    amount = State()

class ChannelPost(StatesGroup):
    message = State()

class BulkUpload(StatesGroup):
    file = State()

class UserLookup(StatesGroup):
    query = State()


class CustomBalance(StatesGroup):
    amount = State()
